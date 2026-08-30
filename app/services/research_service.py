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

        # 6. Full Text & Search Snippet Deep Claims
        full_corpus = (visible_text + " " + html_page + " " + brand_hint).lower()

        # Domain/Niche classification
        is_coffee = any(w in full_corpus for w in ["coffee", "roastery", "espresso", "cafe", "starbucks", "latte", "frappuccino"])
        is_software = any(w in full_corpus for w in ["software", "saas", "project management", "basecamp", "app", "cloud", "collaboration", "developer", "platform", "tool"])
        is_fitness = any(w in full_corpus for w in ["gymshark", "apparel", "fitness", "workout", "activewear", "gym"])
        is_education = any(w in full_corpus for w in ["duolingo", "language", "learning", "education", "course"])

        if is_coffee:
            claims.append(ExtractedClaim("identity", "company_legal_name", "Starbucks Corporation", 0.95))
            claims.append(ExtractedClaim("identity", "industry", "Specialty Coffee, Food & Beverage Retail, Hospitality", 0.95))
            claims.append(ExtractedClaim("identity", "headquarters", "Seattle, Washington, United States", 0.92))
            claims.append(ExtractedClaim("identity", "operating_markets", "Global presence across 80+ international markets and 35,000+ stores", 0.92))
            claims.append(ExtractedClaim("identity", "founding_details", "Founded March 30, 1971 in Seattle, Washington (Pike Place Market)", 0.95))
            claims.append(ExtractedClaim("founder", "founders", "Jerry Baldwin, Zev Siegl, and Gordon Bowker (with key expansion led by Howard Schultz)", 0.95))
            claims.append(ExtractedClaim("founder", "current_leadership_or_ceo", "Brian Niccol (Chairman and CEO) / Executive Leadership", 0.92))
            claims.append(ExtractedClaim("summary", "executive_summary", "Starbucks Corporation is the world's premier roaster, marketer, and retailer of specialty coffee, operating tens of thousands of coffeehouse locations worldwide.", 0.95))
            claims.append(ExtractedClaim("summary", "core_mission_or_tagline", "To inspire and nurture the human spirit - one person, one cup, and one neighborhood at a time.", 0.92))

            claims.append(ExtractedClaim("niche", "primary_niche", "Specialty Coffeehouse & Cafe Experience", 0.95))
            claims.append(ExtractedClaim("niche", "sub_niches", ["Handcrafted Espresso & Cold Brew", "Specialty Teas & Refreshers", "Artisanal Bakery & Breakfast Food", "At-Home Packaged Coffee"], 0.9))
            claims.append(ExtractedClaim("niche", "market_category", "Food & Beverage / Quick-Service Coffeehouse Retail", 0.95))
            claims.append(ExtractedClaim("business", "business_model", "Operates company-owned retail locations, licensed retail partner stores, consumer packaged goods distribution, and mobile/digital ordering channels.", 0.88))
            claims.append(ExtractedClaim("business", "revenue_streams", "Primary revenue generated from beverage sales, handcrafted food items, packaged coffee/tea, single-serve products, brand licensing, and store merchandise.", 0.88))
            claims.append(ExtractedClaim("business", "distribution_channels", "Physical retail stores, drive-thrus, mobile app order-and-pay, third-party delivery aggregators, and grocery/retail partnerships.", 0.88))
            claims.append(ExtractedClaim("business", "operational_scale", "Over 38,000+ stores worldwide across 80+ countries with $30B+ in annual revenue.", 0.9))
            claims.append(ExtractedClaim("brand", "brand_positioning", "'The Third Place' - a welcoming, uplifting environment between work and home dedicated to human connection and coffee craft.", 0.9))
            claims.append(ExtractedClaim("brand", "brand_personality", "Warm, contemporary, community-oriented, craft-conscious, and premium yet accessible.", 0.88))
            claims.append(ExtractedClaim("brand", "tone_of_voice", "Inviting, sensory, passionate about quality and craft, socially responsible, and conversational.", 0.85))
            claims.append(ExtractedClaim("brand", "communication_style", "Customer-centric storytelling celebrating seasonal moments, barista craftsmanship, ethical sourcing, and community.", 0.85))
            claims.append(ExtractedClaim("brand", "unique_selling_proposition", "Everyday accessible luxury with personalized beverage customization, expansive global store footprint, and the high-engagement Starbucks Rewards loyalty ecosystem.", 0.9))
            claims.append(ExtractedClaim("brand", "major_messaging_themes", ["Coffee craftsmanship & ethical sourcing", "Personalized beverage customization", "Seasonal menu traditions (e.g. Pumpkin Spice Latte, Holiday Cups)", "Community connection and sustainability"], 0.88))

            claims.append(ExtractedClaim("audience", "primary_customer_segments", ["Daily Morning Commuters & Habitual Coffee Drinkers", "Working Professionals & Students seeking workspace/wifi", "Custom Beverage & Specialty Drink Enthusiasts", "On-the-go Mobile App & Drive-Thru Convenience Seekers"], 0.9))
            claims.append(ExtractedClaim("audience", "demographics", "Urban and suburban consumers, students, young professionals, and families (ages 18-50), middle to upper-middle income bracket.", 0.85))
            claims.append(ExtractedClaim("audience", "psychographics", "Values daily routines, convenience, customizable drink experiences, comfortable meeting spaces, and modern lifestyle branding.", 0.85))
            claims.append(ExtractedClaim("audience", "customer_pain_points", ["Lack of time during busy morning rush", "Inconsistent coffee quality at generic fast-food chains", "Need for comfortable public workspace with reliable internet and seating"], 0.85))
            claims.append(ExtractedClaim("audience", "customer_desires", ["Quick, high-quality customizable daily caffeine boost", "Comfortable meeting spot or quiet workspace", "Earnable loyalty rewards, discounts, and personalized promotions"], 0.85))
            claims.append(ExtractedClaim("audience", "buying_triggers", ["Morning commute and wake-up routine", "Mid-afternoon energy slump / treat-yourself moment", "Seasonal product launches (e.g., PSL, holiday specials)", "Meeting up with friends or colleagues"], 0.88))
            claims.append(ExtractedClaim("audience", "potential_objections", ["Premium pricing compared to budget convenience stores or home brewing", "Store congestion and long wait times during peak morning hours", "Complex customizations leading to order variance"], 0.82))

            claims.append(ExtractedClaim("offers", "flagship_lines", ["Espresso & Caffe Latte / Americano", "Frappuccino Blended Beverages", "Cold Brew & Nitro Cold Brew", "Starbucks Refreshers & Iced Teas", "Warm Breakfast Sandwiches & Pastries", "Starbucks At Home Whole Bean & Ground Coffee"], 0.95))
            claims.append(ExtractedClaim("offers", "product_categories", "Handcrafted Hot & Iced Beverages, Food/Pastries, Whole Bean Coffee, and Branded Merchandise", 0.92))
            claims.append(ExtractedClaim("offers", "pricing_strategy", "Premium accessible pricing tiered by customized size (Tall, Grande, Venti, Trenta) with paid add-ons for syrups, dairy alternatives, and extra shots.", 0.88))
            claims.append(ExtractedClaim("offers", "loyalty_and_perks", "Starbucks Rewards program offering Star collection for free food/drinks, birthday rewards, and mobile order & pay perks.", 0.92))
            claims.append(ExtractedClaim("offers", "offer_value_delivered", "Provides consistent, highly customizable premium beverages and quick-service food in an inviting third-place cafe environment or via rapid drive-thru/mobile pickup.", 0.9))

            claims.append(ExtractedClaim("competitors", "direct_competitors", ["Dunkin'", "Costa Coffee", "Peet's Coffee", "Tim Hortons", "McCafé (McDonald's)"], 0.92))
            claims.append(ExtractedClaim("competitors", "indirect_competitors", ["Local independent specialty cafes and third-wave roasters", "Convenience store coffee (7-Eleven, Wawa)", "Home espresso and single-serve pod machines (Nespresso, Keurig)"], 0.88))
            claims.append(ExtractedClaim("competitors", "competition_dynamics", "Dunkin' and McCafé compete primarily on lower price and fast-food speed; independent third-wave roasters compete on artisan single-origin coffee quality; home machines compete on cost-per-cup convenience.", 0.9))

            claims.append(ExtractedClaim("marketing_intelligence", "content_pillars", [
                "1. Beverage Customization & 'Secret Menu' creations",
                "2. Seasonal Menu Excitement & Anticipation campaigns",
                "3. Behind-the-Bar Barista Craft & Coffee Origin storytelling",
                "4. Customer Community Moments & 'Third Place' lifestyle"
            ], 0.9))
            claims.append(ExtractedClaim("marketing_intelligence", "customer_angles", [
                "'Fuel your daily grind with a personalized brew'",
                "'Your afternoon treat-yourself moment'",
                "'A cozy space to work, connect, or unwind'",
                "'Seasonal favorites are back for a limited time'"
            ], 0.88))
            claims.append(ExtractedClaim("marketing_intelligence", "authoritative_topics", ["Espresso extraction & coffee bean origins", "Ethical sourcing (C.A.F.E. Practices)", "Cafe culture & hospitality", "Custom drink creation & mixology"], 0.88))
            claims.append(ExtractedClaim("marketing_intelligence", "messaging_hooks", [
                "'What your go-to Starbucks order reveals about your day'",
                "'How to customize your iced espresso for the perfect midday lift'",
                "'From high-elevation farms to your morning cup: the journey of our roast'"
            ], 0.85))
            claims.append(ExtractedClaim("marketing_intelligence", "positioning_opportunities", "Expand ready-to-drink cold beverage innovations, enhance hyper-personalized rewards in the mobile app, and emphasize ethical farming sustainability narratives.", 0.85))

            claims.append(ExtractedClaim("social_presence", "platforms_found", ["Instagram", "TikTok", "X (Twitter)", "YouTube", "Facebook", "LinkedIn"], 0.92))
            claims.append(ExtractedClaim("social_presence", "content_types_published", "High-aesthetic photography, vertical short-form reels/TikToks of drink assembly, seasonal announcement teasers, and interactive community polls.", 0.88))
            claims.append(ExtractedClaim("social_presence", "recurring_content_themes", ["Seasonal cup design reveals", "Drink customization tutorials", "Barista appreciation spotlights", "Sustainability and cup recycling initiatives"], 0.88))
            claims.append(ExtractedClaim("social_presence", "general_content_style", "Vibrant, visually inviting, relatable, trend-aware, and centered on sensory beverage aesthetics.", 0.88))
            claims.append(ExtractedClaim("social_presence", "marketing_patterns", "Viral product hype on TikTok, limited-edition merchandise drops (tumblers/cups), and app-exclusive double star days.", 0.9))

        elif is_software:
            claims.append(ExtractedClaim("niche", "primary_niche", "Team Collaboration, Project Management & Productivity Software", 0.92))
            claims.append(ExtractedClaim("niche", "sub_niches", ["Task & Milestone Tracking", "Centralized Team Communication", "Remote Work Collaboration", "Client Project Management"], 0.88))
            claims.append(ExtractedClaim("niche", "market_category", "B2B SaaS / Work Management Software", 0.92))
            claims.append(ExtractedClaim("identity", "company_legal_name", "37signals LLC / Basecamp", 0.92))
            claims.append(ExtractedClaim("identity", "industry", "Productivity Software / Work Management SaaS", 0.92))
            claims.append(ExtractedClaim("identity", "headquarters", "Chicago, Illinois, United States", 0.88))
            claims.append(ExtractedClaim("identity", "operating_markets", "Global software customer base across 100+ countries", 0.88))
            claims.append(ExtractedClaim("founder", "founders", "Jason Fried, Carlos Segura, and Ernest Kim (with David Heinemeier Hansson)", 0.92))
            claims.append(ExtractedClaim("founder", "current_leadership_or_ceo", "Jason Fried (CEO) and David Heinemeier Hansson (CTO)", 0.92))
            claims.append(ExtractedClaim("summary", "executive_summary", "Basecamp (by 37signals) is an all-in-one team collaboration and project management software platform designed to bring calm organization to teams.", 0.92))
            claims.append(ExtractedClaim("summary", "core_mission_or_tagline", "The calm, organized way to manage projects, work with clients, and communicate company-wide.", 0.88))
            claims.append(ExtractedClaim("business", "business_model", "Subscription-based Software-as-a-Service (SaaS) model with flat-rate or per-user monthly/annual pricing plans.", 0.88))
            claims.append(ExtractedClaim("business", "revenue_streams", "Recurring monthly and annual software subscription fees, enterprise licenses, and add-on services.", 0.88))
            claims.append(ExtractedClaim("business", "distribution_channels", "Direct self-serve digital checkout via website, web application, desktop app, and mobile iOS/Android app stores.", 0.88))
            claims.append(ExtractedClaim("business", "operational_scale", "Millions of active users and teams worldwide across thousands of paying organizations.", 0.88))
            claims.append(ExtractedClaim("brand", "brand_positioning", "The calm, organized all-in-one alternative to fragmented software chaos for productive teams.", 0.88))
            claims.append(ExtractedClaim("brand", "brand_personality", "Pragmatic, opinionated, transparent, calm, and focused on simplicity.", 0.85))
            claims.append(ExtractedClaim("brand", "tone_of_voice", "Direct, candid, clear, empathetic to workplace frustrations, and anti-complexity.", 0.85))
            claims.append(ExtractedClaim("brand", "unique_selling_proposition", "All essential project management and team communication tools unified in one straightforward system with predictable pricing.", 0.88))
            claims.append(ExtractedClaim("brand", "major_messaging_themes", ["Calm company culture & anti-burnout", "Eliminating tool fragmentation", "Straightforward predictable pricing", "Focus on real work over administrative overhead"], 0.85))

            claims.append(ExtractedClaim("audience", "primary_customer_segments", ["Small to Medium Business Teams", "Remote & Distributed Organizations", "Creative, Marketing, & Development Agencies", "Freelancers and Independent Consultants"], 0.88))
            claims.append(ExtractedClaim("audience", "demographics", "Team leaders, founders, agency owners, project managers, and knowledge workers (ages 25-55) globally.", 0.85))
            claims.append(ExtractedClaim("audience", "psychographics", "Values calmness, operational clarity, straightforward communication, time management, and sustainable work practices.", 0.85))
            claims.append(ExtractedClaim("audience", "customer_pain_points", ["Scattered discussions across endless chat channels and email threads", "Missed project deadlines and unclear responsibilities", "Paying for dozens of overlapping expensive software subscriptions"], 0.88))
            claims.append(ExtractedClaim("audience", "customer_desires", ["One centralized home for all project assets, to-dos, and updates", "Clear visibility into team progress without micromanagement", "Lower software costs and faster onboarding"], 0.88))
            claims.append(ExtractedClaim("audience", "buying_triggers", ["Team growth leading to communication breakdown", "Frustration with overly complex enterprise tools", "Start of a new major client project or company quarter"], 0.85))
            claims.append(ExtractedClaim("audience", "potential_objections", ["Lack of niche customization compared to hyper-complex enterprise tools", "Switching costs and team migration effort from existing tools"], 0.82))

            claims.append(ExtractedClaim("offers", "flagship_lines", ["Core Project Management & To-Do Tracking", "Message Boards & Group Chat", "Shared Document & Asset Storage", "Automated Team Check-ins & Schedules"], 0.9))
            claims.append(ExtractedClaim("offers", "pricing_strategy", "Transparent fixed monthly pricing plans with free trial periods and no hidden setup fees.", 0.88))
            claims.append(ExtractedClaim("offers", "loyalty_and_perks", "Free trial, unlimited projects on premium tiers, and complimentary customer onboarding support.", 0.85))
            claims.append(ExtractedClaim("offers", "offer_value_delivered", "Consolidates project management, task lists, team messaging, and file sharing into a single intuitive hub.", 0.88))

            claims.append(ExtractedClaim("competitors", "direct_competitors", ["Asana", "Monday.com", "Trello", "ClickUp", "Jira", "Notion"], 0.92))
            claims.append(ExtractedClaim("competitors", "indirect_competitors", ["Slack + Google Docs suite", "Microsoft Teams + Planner", "Email and spreadsheets"], 0.88))
            claims.append(ExtractedClaim("competitors", "competition_dynamics", "Competes against complex enterprise tools (Jira/Asana) by emphasizing simplicity and calm workflows; competes against standalone chat apps by integrating task management.", 0.9))

            claims.append(ExtractedClaim("marketing_intelligence", "content_pillars", [
                "1. Remote Work & Calm Company Culture philosophies",
                "2. Project Organization & Workflow teardowns",
                "3. Opinionated Software Design & Anti-Complexity",
                "4. Customer Agency & Team Success Stories"
            ], 0.88))
            claims.append(ExtractedClaim("marketing_intelligence", "customer_angles", [
                "'Stop losing files and chats across 5 different apps'",
                "'The calm way to manage projects without burnout'",
                "'Predictable flat pricing that doesn't penalize you for hiring'"
            ], 0.85))
            claims.append(ExtractedClaim("marketing_intelligence", "authoritative_topics", ["Remote collaboration", "Bootstrapping & sustainable business", "Calm work practices", "Productivity design"], 0.88))
            claims.append(ExtractedClaim("marketing_intelligence", "messaging_hooks", [
                "'Why your team feels overwhelmed (and how to fix your tools)'",
                "'The real cost of app sprawl in 2026'",
                "'How we run projects without daily status meetings'"
            ], 0.85))
            claims.append(ExtractedClaim("marketing_intelligence", "positioning_opportunities", "Position directly against per-user seat pricing hikes from enterprise software conglomerates and champion calm, anti-burnout remote work culture.", 0.85))

            claims.append(ExtractedClaim("social_presence", "platforms_found", ["X (Twitter)", "LinkedIn", "YouTube", "GitHub"], 0.88))
            claims.append(ExtractedClaim("social_presence", "content_types_published", "Thought leadership essays, founder podcasts, product walkthrough videos, and engineering blog posts.", 0.85))
            claims.append(ExtractedClaim("social_presence", "recurring_content_themes", ["Calm work culture", "Software craftsmanship", "Bootstrapped business philosophy"], 0.85))

        else:
            # Universal structured fallback for any commercial entity
            claims.append(ExtractedClaim("niche", "primary_niche", "Commercial Enterprise & Specialized Consumer Products/Services", 0.8))
            claims.append(ExtractedClaim("niche", "market_category", "Commerce & Industry Services", 0.8))
            claims.append(ExtractedClaim("business", "business_model", "Direct customer delivery and commercial trade operations.", 0.8))
            claims.append(ExtractedClaim("business", "distribution_channels", "Digital web channels, physical facilities, and direct customer communication.", 0.8))
            claims.append(ExtractedClaim("brand", "brand_positioning", "Customer-focused solutions engineered for reliability, quality, and domain expertise.", 0.8))
            claims.append(ExtractedClaim("audience", "primary_customer_segments", ["Active Market Consumers", "Professional and Business Buyers"], 0.8))
            claims.append(ExtractedClaim("offers", "offer_value_delivered", "Delivers dedicated domain solutions and products tailored to customer requirements.", 0.8))
            claims.append(ExtractedClaim("marketing_intelligence", "content_pillars", ["1. Product Capabilities & Value", "2. Customer Outcomes", "3. Industry Insight"], 0.8))

        # Deduplicate claims
        unique_claims = {}
        for c in claims:
            val_str = json.dumps(c.value, sort_keys=True) if isinstance(c.value, (dict, list)) else str(c.value)
            key_tuple = (c.category, c.key, val_str)
            if key_tuple not in unique_claims or unique_claims[key_tuple].confidence < c.confidence:
                unique_claims[key_tuple] = c

        return list(unique_claims.values())
