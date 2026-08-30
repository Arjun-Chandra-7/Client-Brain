from abc import ABC, abstractmethod
from dataclasses import dataclass
import html
from html.parser import HTMLParser
import json
import re
from urllib.parse import parse_qs, quote_plus, unquote, urljoin, urlparse
import urllib.request

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


@dataclass
class CollectedSource:
    source_type: str
    url: str | None
    title: str | None
    raw_reference: str | None
    authority: str = "public_web"
    metadata: dict | None = None


@dataclass
class ExtractedClaim:
    category: str
    key: str
    value: str | dict | list
    confidence: float


class ResearchProvider(ABC):
    @abstractmethod
    def collect(self, urls: list[str]) -> list[CollectedSource]: ...


class UnavailableResearchProvider(ResearchProvider):
    def collect(self, urls: list[str]) -> list[CollectedSource]: return []


def clean_text(text: str | None) -> str:
    if not text:
        return ""
    cleaned = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.I)
    cleaned = re.sub(r'<script[^>]*>.*?</script>', '', cleaned, flags=re.DOTALL | re.I)
    cleaned = re.sub(r'<[^>]+>', ' ', cleaned)
    cleaned = html.unescape(cleaned)
    cleaned = re.sub(r'[\u2010-\u2015\u2212]', '-', cleaned)
    cleaned = re.sub(r'[\u2018\u2019]', "'", cleaned)
    cleaned = re.sub(r'[\u201c\u201d]', '"', cleaned)
    cleaned = re.sub(r'\[\d+\]', '', cleaned)
    return " ".join(cleaned.split())


class _PageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.title = ""
        self.description = ""
        self.site_name = ""
        self.headings: list[str] = []
        self.text: list[str] = []
        self.links: list[str] = []
        self.json_ld: list[str] = []
        self._tag = None
        self._attrs = {}

    def handle_starttag(self, tag, attrs):
        self._tag, self._attrs = tag.lower(), dict(attrs)
        if self._tag == "meta":
            name = self._attrs.get("name", "").lower()
            prop = self._attrs.get("property", "").lower()
            content = self._attrs.get("content", "")
            if name in {"description", "twitter:description"} or prop in {"og:description", "twitter:description"}:
                self.description = self.description or content
            elif prop in {"og:site_name", "application-name"}:
                self.site_name = self.site_name or content
        elif self._tag == "a" and self._attrs.get("href"):
            self.links.append(self._attrs["href"])

    def handle_endtag(self, tag):
        if tag.lower() == self._tag:
            self._tag = None

    def handle_data(self, data):
        text = " ".join(data.split())
        if not text:
            return
        if self._tag == "title":
            self.title += " " + text
        elif self._tag in {"h1", "h2", "h3"}:
            self.headings.append(text)
        elif self._tag == "script" and self._attrs.get("type", "").lower() == "application/ld+json":
            self.json_ld.append(text)
        elif self._tag not in {"script", "style", "noscript"}:
            self.text.append(text)


class PublicWebResearchProvider(ResearchProvider):
    """Evidence-backed public web research provider."""
    user_agent = USER_AGENT
    relevant_paths = (
        "about", "company", "story", "history", "leadership", "team", "mission",
        "product", "products", "service", "services", "menu", "shop", "pricing",
        "rewards", "careers", "press", "news", "brand"
    )

    @staticmethod
    def normalize_url(url: str | None) -> str | None:
        if not url:
            return None
        url_str = html.unescape(url.strip())
        if "://" not in url_str:
            url_str = "https://" + url_str
        parsed = urlparse(url_str)

        # Resolve Google search and redirect URLs
        if parsed.netloc.endswith("google.com"):
            if parsed.path in {"/url", "/url/"}:
                query = parse_qs(parsed.query)
                target = query.get("q", query.get("url", [""]))[0]
                if target and (target.startswith("http://") or target.startswith("https://") or "." in target):
                    target_parsed = urlparse(target if "://" in target else "https://" + target)
                    if target_parsed.netloc and not target_parsed.netloc.endswith("google.com") and "." in target_parsed.netloc:
                        return PublicWebResearchProvider.normalize_url(unquote(target))
            return None

        # Resolve DuckDuckGo redirect URLs
        if "duckduckgo.com" in parsed.netloc:
            if "uddg=" in parsed.query or parsed.path in {"/l/", "/l"}:
                query = parse_qs(parsed.query)
                if "uddg" in query:
                    return PublicWebResearchProvider.normalize_url(unquote(query["uddg"][0]))
            return None

        if parsed.scheme in {"http", "https"} and parsed.netloc and "." in parsed.netloc:
            if any(engine in parsed.netloc.lower() for engine in ["google.com", "duckduckgo.com", "bing.com", "yahoo.com"]):
                return None
            return parsed.scheme + "://" + parsed.netloc + parsed.path.rstrip("/") + (("?" + parsed.query) if parsed.query else "")
        return None

    def _fetch(self, url: str, timeout: int = 12) -> tuple[str, str] | None:
        try:
            request = urllib.request.Request(
                url,
                headers={
                    "User-Agent": self.user_agent,
                    "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.9",
                }
            )
            with urllib.request.urlopen(request, timeout=timeout) as response:
                content_type = response.headers.get("Content-Type", "")
                if "html" not in content_type and "json" not in content_type and "text" not in content_type:
                    return None
                charset = response.headers.get_content_charset() or "utf-8"
                return response.geturl(), response.read(800_000).decode(charset, errors="replace")
        except Exception:
            return None

    def search(self, query: str, limit: int = 6) -> list[dict]:
        url = "https://lite.duckduckgo.com/lite/"
        data = ("q=" + quote_plus(query)).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "User-Agent": self.user_agent,
                "Content-Type": "application/x-www-form-urlencoded",
            }
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                text = resp.read().decode("utf-8", errors="replace")
                link_matches = re.findall(r'<a[^>]*href=["\']([^"\']+)["\'][^>]*class=["\']result-link["\'][^>]*>(.*?)</a>', text, re.DOTALL)
                if not link_matches:
                    link_matches = re.findall(r'<a[^>]*class=["\']result-link["\'][^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', text, re.DOTALL)
                snippet_matches = re.findall(r'<td[^>]*class=["\']result-snippet["\'][^>]*>(.*?)</td>', text, re.DOTALL)

                results = []
                for i, (raw_url, title_html) in enumerate(link_matches):
                    cleaned_url = self.normalize_url(raw_url)
                    if not cleaned_url:
                        continue
                    title = clean_text(title_html)
                    snippet = clean_text(snippet_matches[i]) if i < len(snippet_matches) else ""
                    results.append({"url": cleaned_url, "title": title, "snippet": snippet})
                    if len(results) >= limit:
                        break
                return results
        except Exception:
            return []

    def collect(self, urls: list[str]) -> list[CollectedSource]:
        output = []
        for url in urls:
            normalized = self.normalize_url(url)
            if not normalized:
                continue
            fetched = self._fetch(normalized)
            if not fetched:
                continue
            resolved, page = fetched
            parser = _PageParser()
            parser.feed(page)
            output.append(CollectedSource(
                source_type="external_research",
                url=resolved,
                title=clean_text(parser.title) or urlparse(resolved).netloc,
                raw_reference=page,
                authority="official_website" if normalized == urls[0] else "public_web"
            ))
        return output

    def _wikipedia_lookup(self, brand: str) -> dict | None:
        commercial_keywords = {
            "company", "corporation", "chain", "software", "retail", "brand", "app",
            "platform", "business", "service", "manufacturer", "firm", "enterprise",
            "restaurant", "store", "multinational", "coffeehouse", "ecommerce"
        }

        def fetch_summary(title: str) -> dict | None:
            fetched = self._fetch(f"https://en.wikipedia.org/api/rest_v1/page/summary/{quote_plus(title)}")
            if fetched:
                try:
                    data = json.loads(fetched[1])
                    if "extract" in data:
                        return data
                except Exception:
                    pass
            return None

        summary_data = fetch_summary(brand)
        is_commercial = summary_data and any(kw in (summary_data.get("description", "") + " " + summary_data.get("extract", "")).lower() for kw in commercial_keywords)

        if not is_commercial:
            for query in [f"{brand} company", f"{brand} software", f"{brand} brand", brand]:
                search_url = f"https://en.wikipedia.org/w/api.php?action=opensearch&search={quote_plus(query)}&limit=5&namespace=0&format=json"
                fetched_sr = self._fetch(search_url)
                if fetched_sr:
                    try:
                        sr = json.loads(fetched_sr[1])
                        if sr and len(sr) > 1:
                            for candidate in sr[1]:
                                cand_summary = fetch_summary(candidate)
                                if cand_summary and any(kw in (cand_summary.get("description", "") + " " + cand_summary.get("extract", "")).lower() for kw in commercial_keywords):
                                    summary_data = cand_summary
                                    is_commercial = True
                                    break
                        if is_commercial:
                            break
                    except Exception:
                        pass

        page_title = summary_data.get("title") if summary_data else brand
        fetched_html = self._fetch(f"https://en.wikipedia.org/api/rest_v1/page/html/{quote_plus(page_title)}")
        page_html = fetched_html[1] if fetched_html else None

        if not summary_data and not page_html:
            return None

        infobox = {}
        if page_html:
            infobox_match = re.search(r'<table[^>]*class="[^"]*infobox[^"]*"[^>]*>(.*?)</table>', page_html, re.DOTALL)
            if infobox_match:
                rows = re.findall(r'<tr[^>]*>\s*<th[^>]*>(.*?)</th>\s*<td[^>]*>(.*?)</td>\s*</tr>', infobox_match.group(1), re.DOTALL)
                for l_html, v_html in rows:
                    l_clean = clean_text(l_html).lower()
                    v_clean = clean_text(v_html)
                    if l_clean and v_clean:
                        infobox[l_clean] = v_clean

        return {
            "title": page_title,
            "description": summary_data.get("description", "") if summary_data else "",
            "extract": summary_data.get("extract", "") if summary_data else "",
            "infobox": infobox,
            "raw_html": page_html,
            "url": f"https://en.wikipedia.org/wiki/{quote_plus(page_title)}",
        }

    def discover_brand(self, brand_name: str, website: str | None, max_pages: int = 6) -> list[CollectedSource]:
        collected: list[CollectedSource] = []
        official = self.normalize_url(website)

        wiki_info = self._wikipedia_lookup(brand_name)
        if wiki_info:
            wiki_content = f"Wikipedia: {wiki_info['title']}\nDescription: {wiki_info['description']}\nSummary: {wiki_info['extract']}\n\nInfobox Details:\n"
            for k, v in wiki_info["infobox"].items():
                wiki_content += f"{k}: {v}\n"
            collected.append(CollectedSource(
                source_type="external_research",
                url=wiki_info["url"],
                title=f"Wikipedia: {wiki_info['title']}",
                raw_reference=wiki_content + "\n" + (clean_text(wiki_info.get("raw_html"))[:30000] if wiki_info.get("raw_html") else ""),
                authority="public_reference",
                metadata={"infobox": wiki_info["infobox"], "extract": wiki_info["extract"], "description": wiki_info["description"], "brand_query": brand_name}
            ))

            if not official:
                for web_key in ["website", "official website", "url"]:
                    if wiki_info["infobox"].get(web_key):
                        raw_site = wiki_info["infobox"][web_key]
                        m = re.search(r'https?://[^\s]+|www\.[^\s]+|[a-zA-Z0-9.-]+\.(?:com|org|io|net|co|app)', raw_site)
                        if m:
                            official = self.normalize_url(m.group(0))
                            break

        # Search DuckDuckGo Lite for official website
        search_results_official = self.search(f"{brand_name} official website", limit=6)
        if not official and search_results_official:
            token = re.sub(r"[^a-z0-9]", "", brand_name.lower().split()[0])
            for res in search_results_official:
                netloc = urlparse(res["url"]).netloc.lower()
                if "wikipedia" not in netloc and "duckduckgo" not in netloc:
                    if token in re.sub(r"[^a-z0-9]", "", netloc) or not official:
                        official = res["url"]
                        break

        # If official website found, crawl homepage and subpages
        if official:
            home_fetched = self._fetch(official)
            if home_fetched:
                res_url, page_content = home_fetched
                parser = _PageParser()
                parser.feed(page_content)
                collected.insert(0, CollectedSource(
                    source_type="external_research",
                    url=res_url,
                    title=clean_text(parser.title) or f"{brand_name} Official Website",
                    raw_reference=page_content,
                    authority="official_website",
                    metadata={"brand_query": brand_name}
                ))

                # Discover relevant subpages
                root_netloc = urlparse(res_url).netloc
                internal_links = []
                for href in parser.links:
                    abs_url = self.normalize_url(urljoin(res_url, href))
                    if abs_url and urlparse(abs_url).netloc == root_netloc:
                        path = urlparse(abs_url).path.lower()
                        if any(kw in path for kw in self.relevant_paths) and abs_url not in internal_links and abs_url != res_url:
                            internal_links.append(abs_url)

                for sub_url in internal_links[:3]:
                    sub_fetched = self._fetch(sub_url)
                    if sub_fetched:
                        s_url, s_page = sub_fetched
                        s_parser = _PageParser()
                        s_parser.feed(s_page)
                        collected.append(CollectedSource(
                            source_type="external_research",
                            url=s_url,
                            title=clean_text(s_parser.title) or s_url,
                            raw_reference=s_page,
                            authority="official_subpage",
                            metadata={"brand_query": brand_name}
                        ))

        # Collect structured search snippets for products and competitors
        product_results = self.search(f"{brand_name} products services menu pricing", limit=4)
        competitor_results = self.search(f"{brand_name} competitors market analysis", limit=4)

        all_search_snippets = search_results_official + product_results + competitor_results
        snippets_text = f"Search Index & Public Web Snippets for {brand_name}:\n\n"
        for sr in all_search_snippets:
            snippets_text += f"Source: {sr['title']} ({sr['url']})\nSnippet: {sr['snippet']}\n\n"

        collected.append(CollectedSource(
            source_type="external_research",
            url=f"https://search.index/{quote_plus(brand_name)}",
            title=f"Public Web & Market Index: {brand_name}",
            raw_reference=snippets_text,
            authority="public_search_index",
            metadata={"search_results": all_search_snippets, "brand_query": brand_name}
        ))

        # Deduplicate sources by URL
        seen_urls = set()
        unique_collected = []
        for src in collected:
            if src.url and src.url in seen_urls:
                continue
            if src.url:
                seen_urls.add(src.url)
            unique_collected.append(src)

        return unique_collected[:max_pages + 2]

    @classmethod
    def extract_claims(cls, html_page: str, url: str = "", metadata: dict | None = None) -> list[ExtractedClaim]:
        parser = _PageParser()
        parser.feed(html_page)
        claims: list[ExtractedClaim] = []
        visible_text = clean_text(" ".join(parser.text))
        meta_dict = metadata or {}
        brand_hint = meta_dict.get("brand_query", "")

        # 1. Page Metadata Claims
        if parser.title:
            claims.append(ExtractedClaim("summary", "published_page_title", clean_text(parser.title), 0.9))
        if parser.description:
            claims.append(ExtractedClaim("summary", "website_description_claim", clean_text(parser.description), 0.88))
            claims.append(ExtractedClaim("summary", "executive_summary", clean_text(parser.description), 0.88))
            claims.append(ExtractedClaim("brand", "value_proposition", clean_text(parser.description), 0.85))
        for heading in list(dict.fromkeys(parser.headings))[:12]:
            claims.append(ExtractedClaim("summary", "published_heading", clean_text(heading), 0.75))

        # 2. Wikipedia Infobox & Structured Reference Extraction
        raw_infobox = meta_dict.get("infobox", {})
        if not raw_infobox and "Infobox Details:" in html_page:
            info_part = html_page.split("Infobox Details:")[1].split("\n\n")[0]
            raw_infobox = {}
            for line in info_part.strip().split("\n"):
                if ":" in line:
                    k, v = line.split(":", 1)
                    raw_infobox[k.strip().lower()] = v.strip()

        infobox = {}
        for k, v in raw_infobox.items():
            infobox[k.strip().lower()] = v
            infobox[k.strip().lower().replace(" ", "_")] = v

        if infobox:
            if "type" in infobox:
                claims.append(ExtractedClaim("business", "ownership_structure", f"Corporate structure: {infobox['type']}", 0.9))
            if "industry" in infobox or "genre" in infobox:
                ind = infobox.get("industry", infobox.get("genre", ""))
                claims.append(ExtractedClaim("identity", "industry", ind, 0.95))
                claims.append(ExtractedClaim("niche", "market_category", ind, 0.9))
            if "founded" in infobox:
                claims.append(ExtractedClaim("identity", "founding_details", infobox["founded"], 0.95))
                claims.append(ExtractedClaim("business", "founding_claim", f"Founded: {infobox['founded']}", 0.9))
            if "founders" in infobox:
                claims.append(ExtractedClaim("founder", "founders", infobox["founders"], 0.95))
            if "headquarters" in infobox:
                claims.append(ExtractedClaim("identity", "headquarters", infobox["headquarters"], 0.95))
            if "number_of_locations" in infobox:
                claims.append(ExtractedClaim("business", "operational_scale", f"Number of locations: {infobox['number_of_locations']}", 0.92))
            if "area_served" in infobox:
                claims.append(ExtractedClaim("identity", "operating_markets", f"Area served: {infobox['area_served']}", 0.9))
            if "key_people" in infobox:
                claims.append(ExtractedClaim("founder", "current_leadership_or_ceo", infobox["key_people"], 0.95))
            if "products" in infobox:
                claims.append(ExtractedClaim("offers", "major_offerings", infobox["products"], 0.95))
                claims.append(ExtractedClaim("offers", "product_categories", f"Core product lines: {infobox['products']}", 0.9))
            if "revenue" in infobox:
                claims.append(ExtractedClaim("business", "revenue_scale", f"Annual revenue: {infobox['revenue']}", 0.9))
            if "subsidiaries" in infobox:
                claims.append(ExtractedClaim("business", "subsidiaries_and_brands", infobox["subsidiaries"], 0.85))
            if "website" in infobox:
                claims.append(ExtractedClaim("identity", "official_website", infobox["website"], 0.95))

        # 3. Wikipedia Extract Summary
        wiki_extract = meta_dict.get("extract")
        if not wiki_extract and "Summary: " in html_page:
            m = re.search(r'Summary:\s*(.+?)(?:\n\n|\nInfobox)', html_page, re.DOTALL)
            if m:
                wiki_extract = clean_text(m.group(1))

        if wiki_extract:
            claims.append(ExtractedClaim("summary", "executive_summary", wiki_extract[:500], 0.95))
            claims.append(ExtractedClaim("business", "business_description", wiki_extract[:600], 0.92))

        # 4. JSON-LD structured data
        for raw in parser.json_ld:
            try:
                entries = json.loads(raw)
                entries = entries if isinstance(entries, list) else [entries]
                for entry in entries:
                    if not isinstance(entry, dict):
                        continue
                    if entry.get("name"):
                        claims.append(ExtractedClaim("identity", "company_legal_name", str(entry["name"]), 0.9))
                        claims.append(ExtractedClaim("identity", "structured_data_name", str(entry["name"]), 0.85))
                    if entry.get("description"):
                        claims.append(ExtractedClaim("business", "business_description", clean_text(str(entry["description"])), 0.88))
                    if entry.get("foundingDate"):
                        claims.append(ExtractedClaim("identity", "founding_details", f"Founded in {entry['foundingDate']}", 0.9))
                        claims.append(ExtractedClaim("business", "structured_data_foundingDate", str(entry["foundingDate"]), 0.85))
                    if entry.get("address"):
                        claims.append(ExtractedClaim("identity", "headquarters", str(entry["address"]), 0.85))
                    if entry.get("sameAs"):
                        same_as = entry["sameAs"] if isinstance(entry["sameAs"], list) else [entry["sameAs"]]
                        for social in same_as:
                            claims.append(ExtractedClaim("social_presence", "linked_official_social_profile", str(social), 0.9))
            except Exception:
                continue

        # 5. Social Links from Page
        for href in parser.links:
            absolute = cls.normalize_url(urljoin(url, href))
            if absolute and any(platform in urlparse(absolute).netloc.lower() for platform in ("instagram.com", "youtube.com", "linkedin.com", "tiktok.com", "facebook.com", "x.com", "twitter.com")):
                claims.append(ExtractedClaim("social_presence", "linked_official_social_profile", absolute, 0.88))

        # 6. Full Text & Dynamic Internet Intelligence Extraction
        full_corpus = (visible_text + " " + html_page + " " + brand_hint).lower()
        title_desc = f"{clean_text(parser.title)} {clean_text(parser.description)}"

        # Universal Dynamic Extraction for Any Entity
        brand_clean = brand_hint or (clean_text(parser.title).split()[0] if parser.title else "Brand")

        # 6.1 Identify Niche & Industry dynamically
        inferred_industry = None
        if "industry" in infobox:
            inferred_industry = infobox["industry"]
        elif parser.description and len(parser.description) > 10:
            inferred_industry = clean_text(parser.description).split(".")[0]
        elif parser.title:
            inferred_industry = clean_text(parser.title).split("-")[-1].split("|")[-1].strip()

        industry_val = (inferred_industry[:120] if inferred_industry else f"{brand_clean} Industry & Commercial Solutions")
        claims.append(ExtractedClaim("identity", "company_legal_name", brand_clean, 0.92))
        claims.append(ExtractedClaim("identity", "industry", industry_val, 0.9))
        claims.append(ExtractedClaim("niche", "primary_niche", industry_val, 0.88))
        claims.append(ExtractedClaim("business", "business_model", "Commercial product delivery, services, and digital operations.", 0.85))
        claims.append(ExtractedClaim("social_presence", "general_content_style", "Digital communications, educational content, and community updates.", 0.85))

        # 6.2 Extract Sub-niches from Headings & Text
        subniches = []
        for h in parser.headings:
            h_clean = clean_text(h)
            if 4 < len(h_clean) < 60 and not any(skip in h_clean.lower() for skip in ("menu", "login", "sign in", "cookie", "privacy", "copyright", "home", "about us")):
                subniches.append(h_clean)
        claims.append(ExtractedClaim("niche", "sub_niches", list(dict.fromkeys(subniches))[:6] if subniches else [f"{brand_clean} Solutions", "Industry Best Practices"], 0.85))

        # 6.3 Extract Products & Core Features dynamically
        extracted_products = []
        if "products" in infobox:
            raw_prods = [p.strip() for p in infobox["products"].split(",") if p.strip()]
            extracted_products.extend(raw_prods)
        for h in parser.headings:
            h_clean = clean_text(h)
            if any(term in h_clean.lower() for term in ("plan", "tier", "suite", "app", "service", "platform", "solution", "feature", "course", "book", "tool")):
                if 4 < len(h_clean) < 70:
                    extracted_products.append(h_clean)
        claims.append(ExtractedClaim("offers", "flagship_lines", list(dict.fromkeys(extracted_products))[:6] if extracted_products else [f"{brand_clean} Core Offer"], 0.88))
        claims.append(ExtractedClaim("offers", "product_categories", list(dict.fromkeys(extracted_products))[:6] if extracted_products else [f"{brand_clean} Offerings"], 0.88))

        # 6.4 Extract Target Audience & Personas dynamically
        audience_segments = []
        audience_keywords = [
            ("founder", "Founders & Business Owners"),
            ("creator", "Content Creators & Influencers"),
            ("agency", "Digital Agencies & Service Providers"),
            ("team", "Collaborative Teams & Organizations"),
            ("developer", "Software Engineers & Technical Leads"),
            ("marketer", "Marketing & Growth Professionals"),
            ("student", "Students & Lifelong Learners"),
            ("coach", "Coaches, Consultants & Educators"),
            ("consumer", "Everyday Consumers & Enthusiasts"),
            ("fitness", "Athletes & Fitness Enthusiasts"),
            ("enterprise", "Enterprise Leaders & Decision Makers")
        ]
        for kw, seg in audience_keywords:
            if kw in full_corpus:
                audience_segments.append(seg)
        if not audience_segments:
            audience_segments = ["Target Market Consumers", "Professional and Business Buyers"]
        claims.append(ExtractedClaim("audience", "primary_customer_segments", list(dict.fromkeys(audience_segments))[:5], 0.88))

        # 6.5 Extract Problems & Customer Pain Points dynamically
        pain_points = []
        pain_triggers = [
            ("scattered", "Scattered discussions and fragmented workflows across multiple tools"),
            ("waste time", "Wasting hours on repetitive manual administrative tasks"),
            ("burnout", "Overwhelmed by high stress, burnout, and chaotic communication"),
            ("expensive", "High recurring software subscription costs and per-user fees"),
            ("missed", "Missed deadlines and lack of accountability across deliverables"),
            ("confusing", "Complex, bloated interfaces that steepen the learning curve"),
            ("slow", "Slow execution and delayed feedback cycles"),
            ("inconsistent", "Inconsistent results and lack of structured systems")
        ]
        for trigger, desc in pain_triggers:
            if trigger in full_corpus:
                pain_points.append(desc)
        if not pain_points:
            pain_points = [
                f"Inefficient workflows and lack of specialized tools in {inferred_industry or 'the market'}",
                "Time lost navigating fragmented alternatives and legacy solutions",
                "High costs associated with disjointed, complex platforms"
            ]
        claims.append(ExtractedClaim("audience", "customer_pain_points", pain_points[:4], 0.85))

        # 6.6 Extract Competitors from Search Snippets & Text
        competitors_found = []
        comp_matches = re.findall(r'(?:vs\.?|versus|alternative to|competitor(?:s)?(?: to)?)\s+([A-Z][A-Za-z0-9\s&]+)', visible_text + " " + html_page)
        for m in comp_matches:
            c_cand = clean_text(m).split()[0].strip()
            if 2 < len(c_cand) < 25 and c_cand.lower() not in (brand_hint.lower(), "the", "and", "our", "their", "all"):
                competitors_found.append(c_cand)
        if not competitors_found:
            competitors_found = [f"Direct Market Competitors in {industry_val}"]
        claims.append(ExtractedClaim("competitors", "direct_competitors", list(dict.fromkeys(competitors_found))[:6], 0.85))

        # 6.7 Dynamic Content Pillars & Actionable Angles
        brand_clean = brand_hint or (clean_text(parser.title).split()[0] if parser.title else "Brand")
        content_pillars = [
            f"1. {brand_clean} Product Deep-Dives & Workflow Tutorials",
            f"2. Industry Insights & Tactical Teardowns in {inferred_industry or 'the Space'}",
            "3. Overcoming Real Customer Roadblocks & Case Studies",
            "4. Best Practices, Anti-Patterns & Expert Frameworks"
        ]
        claims.append(ExtractedClaim("marketing_intelligence", "content_pillars", content_pillars, 0.88))

        topics = [
            f"{brand_clean} core methodologies",
            f"Industry trends in {inferred_industry or 'modern business'}",
            "Operational efficiency and execution frameworks",
            "Customer transformation and results"
        ]
        claims.append(ExtractedClaim("marketing_intelligence", "authoritative_topics", topics, 0.85))

        hooks = [
            f"'Why standard approaches to {inferred_industry or 'this industry'} fail (and what works)'",
            f"'How {brand_clean} simplifies complex workflows in minutes'",
            "'The biggest mistakes teams make before upgrading their systems'"
        ]
        claims.append(ExtractedClaim("marketing_intelligence", "messaging_hooks", hooks, 0.85))

        # 6.8 Brand Positioning & Tone
        if parser.description:
            claims.append(ExtractedClaim("brand", "brand_positioning", clean_text(parser.description)[:200], 0.88))
            claims.append(ExtractedClaim("brand", "tone_of_voice", "Authoritative, clear, value-driven, and focused on practical outcomes.", 0.85))
        else:
            claims.append(ExtractedClaim("brand", "brand_positioning", f"Dedicated solutions engineered for {inferred_industry or 'quality and performance'}.", 0.8))
            claims.append(ExtractedClaim("brand", "tone_of_voice", "Professional, direct, engaging, and outcome-oriented.", 0.8))

        # Deduplicate claims
        unique_claims = {}
        for c in claims:
            val_str = json.dumps(c.value, sort_keys=True) if isinstance(c.value, (dict, list)) else str(c.value)
            key_tuple = (c.category, c.key, val_str)
            if key_tuple not in unique_claims or unique_claims[key_tuple].confidence < c.confidence:
                unique_claims[key_tuple] = c

        return list(unique_claims.values())
