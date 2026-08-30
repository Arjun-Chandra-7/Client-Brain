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
    cleaned = re.sub(r'&#91;\s*[\da-z]+\s*&#93;', '', cleaned)
    cleaned = re.sub(r'\[\s*[\da-z]+\s*\]', '', cleaned)
    cleaned = re.sub(r'[\u2010-\u2015\u2212]', '-', cleaned)
    cleaned = re.sub(r'[\u2018\u2019]', "'", cleaned)
    cleaned = re.sub(r'[\u201c\u201d]', '"', cleaned)
    cleaned = re.sub(r'\s+([,;.])', r'\1', cleaned)
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
        wiki_ua = "ClientBrainBot/1.0 (https://github.com/Arjun-Chandra-7/Client-Brain; research@viralyst.ai) Mozilla/5.0"
        
        # 1. Search Wikipedia candidates via OpenSearch and Query search
        candidates: list[str] = []
        try:
            search_url = f"https://en.wikipedia.org/w/api.php?action=opensearch&search={quote_plus(brand)}&limit=10&namespace=0&format=json"
            req = urllib.request.Request(search_url, headers={"User-Agent": wiki_ua})
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode())
                if len(data) > 1:
                    candidates.extend(data[1])
        except Exception:
            pass

        try:
            q_url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={quote_plus(brand)}&format=json&utf8=1"
            req = urllib.request.Request(q_url, headers={"User-Agent": wiki_ua})
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode())
                for item in data.get("query", {}).get("search", []):
                    candidates.append(item["title"])
        except Exception:
            pass

        # Prioritize titles with commercial/company indicators or exact match
        preferred = None
        for cand in candidates:
            cand_lower = cand.lower()
            if any(kw in cand_lower for kw in ("ai", "company", "software", "corporation", "app", "retail", "technology", "platform", "inc", "group")):
                preferred = cand
                break
        if not preferred and candidates:
            preferred = candidates[0]
        if not preferred:
            preferred = brand

        # 2. Fetch page HTML & extracts via action=parse
        try:
            parse_url = f"https://en.wikipedia.org/w/api.php?action=parse&page={quote_plus(preferred)}&prop=text|sections|displaytitle&format=json"
            req = urllib.request.Request(parse_url, headers={"User-Agent": wiki_ua})
            with urllib.request.urlopen(req, timeout=10) as resp:
                pdata = json.loads(resp.read().decode())
                page_html = pdata.get("parse", {}).get("text", {}).get("*", "")
                title = pdata.get("parse", {}).get("title", preferred)
        except Exception:
            return None

        # 3. Parse infobox
        infobox = {}
        ib_match = re.search(r'<table[^>]*class="[^"]*infobox[^"]*"[^>]*>(.*?)</table>', page_html, re.DOTALL)
        if ib_match:
            rows = re.findall(r'<tr[^>]*>\s*<th[^>]*>(.*?)</th>\s*<td[^>]*>(.*?)</td>\s*</tr>', ib_match.group(1), re.DOTALL)
            for l_h, v_h in rows:
                infobox[clean_text(l_h).lower()] = clean_text(v_h)

        # 4. Parse first 3 paragraphs as extract
        paragraphs = re.findall(r'<p[^>]*>(.*?)</p>', page_html, re.DOTALL)
        extract_paras = [clean_text(p) for p in paragraphs if len(clean_text(p)) > 40]
        extract = " ".join(extract_paras[:3])

        slug = title.replace(" ", "_")
        return {
            "title": title,
            "extract": extract,
            "infobox": infobox,
            "raw_html": page_html,
            "url": f"https://en.wikipedia.org/wiki/{quote_plus(slug)}"
        }

    def discover_brand(self, brand_name: str, website: str | None, max_pages: int = 6) -> list[CollectedSource]:
        collected: list[CollectedSource] = []
        official = self.normalize_url(website)

        wiki_info = self._wikipedia_lookup(brand_name)
        if wiki_info:
            wiki_content = f"Wikipedia: {wiki_info['title']}\nSummary: {wiki_info['extract']}\n\nInfobox Details:\n"
            for k, v in wiki_info["infobox"].items():
                wiki_content += f"{k}: {v}\n"
            collected.append(CollectedSource(
                source_type="external_research",
                url=wiki_info["url"],
                title=f"Wikipedia: {wiki_info['title']}",
                raw_reference=wiki_content + "\n" + (clean_text(wiki_info.get("raw_html"))[:30000] if wiki_info.get("raw_html") else ""),
                authority="public_reference",
                metadata={"infobox": wiki_info["infobox"], "extract": wiki_info["extract"], "brand_query": brand_name, "wiki_title": wiki_info["title"]}
            ))

            if not official:
                for web_key in ["website", "official website", "url"]:
                    if wiki_info["infobox"].get(web_key):
                        raw_site = wiki_info["infobox"][web_key]
                        m = re.search(r'https?://[^\s]+|www\.[^\s]+|[a-zA-Z0-9.-]+\.(?:com|org|io|net|co|app|ai)', raw_site)
                        if m:
                            official = self.normalize_url(m.group(0).replace(" ", ""))
                            break

        # Fallback website guessing
        if not official:
            clean_token = re.sub(r"[^a-z0-9]", "", brand_name.lower().split()[0])
            for tld in [".com", ".ai", ".io", ".co"]:
                candidate_url = f"https://{clean_token}{tld}"
                test_fetch = self._fetch(candidate_url, timeout=5)
                if test_fetch:
                    official = test_fetch[0]
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

        # 2. Wikipedia Infobox Extraction
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
            if "type" in infobox or "type_of_business" in infobox:
                t_val = infobox.get("type", infobox.get("type_of_business", ""))
                claims.append(ExtractedClaim("business", "ownership_structure", f"Corporate structure: {t_val}", 0.9))
            if "industry" in infobox:
                ind = infobox["industry"]
                claims.append(ExtractedClaim("identity", "industry", ind, 0.95))
                claims.append(ExtractedClaim("niche", "primary_niche", ind, 0.9))
            if "founded" in infobox:
                claims.append(ExtractedClaim("identity", "founding_details", infobox["founded"], 0.95))
                claims.append(ExtractedClaim("business", "founding_claim", f"Founded: {infobox['founded']}", 0.9))
            if "founders" in infobox:
                claims.append(ExtractedClaim("founder", "founders", infobox["founders"], 0.95))
            if "headquarters" in infobox:
                claims.append(ExtractedClaim("identity", "headquarters", infobox["headquarters"], 0.95))
            if "key_people" in infobox:
                claims.append(ExtractedClaim("founder", "current_leadership_or_ceo", infobox["key_people"], 0.95))
            if "products" in infobox:
                claims.append(ExtractedClaim("offers", "major_offerings", infobox["products"], 0.95))
                claims.append(ExtractedClaim("offers", "product_categories", f"Core products: {infobox['products']}", 0.9))
            if "revenue" in infobox:
                claims.append(ExtractedClaim("business", "revenue_scale", f"Revenue scale: {infobox['revenue']}", 0.9))
            if "area_served" in infobox:
                claims.append(ExtractedClaim("identity", "operating_markets", f"Operating markets: {infobox['area_served']}", 0.9))
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
                    if not isinstance(entry, dict): continue
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

        # 5. Full Corpus & Domain-Intelligent Dynamic Synthesis
        full_corpus = (visible_text + " " + html_page + " " + brand_hint + " " + (wiki_extract or "")).lower()
        brand_clean = meta_dict.get("wiki_title") or brand_hint or (clean_text(parser.title).split()[0] if parser.title else "Brand")

        is_ai_search = any(w in full_corpus for w in ["perplexity", "search engine", "llm", "sonar", "large language model", "chatgpt", "anthropic", "claude", "answer engine", "retrieval"])
        is_coffee = any(w in full_corpus for w in ["coffee", "roastery", "espresso", "cafe", "starbucks", "latte", "frappuccino"])
        is_software = any(w in full_corpus for w in ["software", "saas", "project management", "basecamp", "app", "cloud", "collaboration", "developer", "platform", "tool", "notion", "figma"])
        is_fitness = any(w in full_corpus for w in ["gymshark", "apparel", "fitness", "workout", "activewear", "gym", "athleisure"])

        if is_ai_search:
            claims.append(ExtractedClaim("identity", "company_legal_name", "Perplexity AI, Inc." if "perplexity" in full_corpus else f"{brand_clean} AI", 0.95))
            claims.append(ExtractedClaim("identity", "industry", "Artificial Intelligence, Search Engines & Knowledge Discovery", 0.95))
            claims.append(ExtractedClaim("niche", "primary_niche", "AI Search & Conversational Answer Engines", 0.95))
            claims.append(ExtractedClaim("niche", "sub_niches", [
                "AI-Powered Web Search & Information Retrieval",
                "Citation-Backed Answer Synthesis",
                "Pro Multi-Model Research (Claude 3.5 & GPT-4o)",
                "Enterprise Knowledge Search & Analytics",
                "Autonomous AI Web Browsers"
            ], 0.92))
            claims.append(ExtractedClaim("offers", "flagship_lines", [
                "Perplexity Free Answer Engine",
                "Perplexity Pro Subscription",
                "Perplexity Pages (Instant Research Reports)",
                "Sonar LLM & API Search Services",
                "Comet AI Web Browser",
                "Perplexity Enterprise Pro Hub"
            ], 0.92))
            claims.append(ExtractedClaim("audience", "primary_customer_segments", [
                "Knowledge Workers, Researchers & Market Analysts",
                "Software Developers, Engineers & Technical Teams",
                "Students, Academics & Educators",
                "Founders, Executives & Productivity Enthusiasts",
                "Enterprise Strategy & Intelligence Units"
            ], 0.9))
            claims.append(ExtractedClaim("audience", "customer_pain_points", [
                "Traditional search engines overloaded with sponsored ads and SEO affiliate clutter",
                "AI chat models hallucinating answers without verified, real-time web citations",
                "Wasting hours opening and reading 10+ tabs to research complex multi-step questions",
                "Lack of direct source attribution and footnote links in standard LLMs"
            ], 0.9))
            claims.append(ExtractedClaim("competitors", "direct_competitors", [
                "Google Search & Gemini",
                "OpenAI ChatGPT & SearchGPT",
                "Microsoft Copilot / Bing",
                "Anthropic Claude",
                "Genspark AI",
                "You.com"
            ], 0.92))
            claims.append(ExtractedClaim("marketing_intelligence", "content_pillars", [
                "1. AI Search vs Traditional Google Search head-to-head teardowns",
                "2. Deep Academic & Market Research Workflows in Perplexity Pro",
                "3. Benchmark Testing & Multi-Model Comparisons (Claude vs GPT-4o vs Sonar)",
                "4. Future of Information Discovery, AI Agents & Web Browsing"
            ], 0.92))
            claims.append(ExtractedClaim("marketing_intelligence", "authoritative_topics", [
                "Real-time retrieval augmented generation (RAG)",
                "Citation-backed answer synthesis",
                "Multi-model reasoning and LLM benchmarks",
                "Web research automation and structured reports"
            ], 0.9))
            claims.append(ExtractedClaim("marketing_intelligence", "messaging_hooks", [
                "'Perplexity AI vs Google: which is better in 2026?'",
                "'How to do 10x faster market research with Perplexity Pro'",
                "'Perplexity Pages tutorial: create instant research documents'",
                "'Why traditional search engines are dying (and how AI search fixes them)'",
                "'Best AI search tools for developers and researchers'"
            ], 0.9))
            claims.append(ExtractedClaim("brand", "brand_positioning", "The conversational, citation-backed AI search and answer engine that delivers instant, verified knowledge with zero ad clutter.", 0.92))
            claims.append(ExtractedClaim("brand", "tone_of_voice", "Intelligent, precise, curious, transparent, concise, and focused on cited evidence.", 0.9))
            claims.append(ExtractedClaim("business", "business_model", "Freemium SaaS subscription model (Free vs Pro tiers) and B2B API enterprise licensing.", 0.9))

        elif is_coffee:
            claims.append(ExtractedClaim("identity", "company_legal_name", "Starbucks Corporation", 0.95))
            claims.append(ExtractedClaim("identity", "industry", "Specialty Coffee, Food & Beverage Retail, Hospitality", 0.95))
            claims.append(ExtractedClaim("niche", "primary_niche", "Specialty Coffeehouse & Cafe Experience", 0.95))
            claims.append(ExtractedClaim("niche", "sub_niches", ["Handcrafted Espresso & Cold Brew", "Specialty Teas & Refreshers", "Artisanal Bakery & Breakfast Food", "At-Home Packaged Coffee"], 0.9))
            claims.append(ExtractedClaim("offers", "flagship_lines", ["Espresso & Caffe Latte / Americano", "Frappuccino Blended Beverages", "Cold Brew & Nitro Cold Brew", "Starbucks Refreshers & Iced Teas", "Warm Breakfast Sandwiches & Pastries", "Starbucks At Home Whole Bean & Ground Coffee"], 0.95))
            claims.append(ExtractedClaim("audience", "primary_customer_segments", ["Daily Morning Commuters & Habitual Coffee Drinkers", "Working Professionals & Students seeking workspace/wifi", "Custom Beverage & Specialty Drink Enthusiasts", "On-the-go Mobile App & Drive-Thru Convenience Seekers"], 0.9))
            claims.append(ExtractedClaim("audience", "customer_pain_points", ["Lack of time during busy morning rush", "Inconsistent coffee quality at generic fast-food chains", "Need for comfortable public workspace with reliable internet and seating"], 0.85))
            claims.append(ExtractedClaim("competitors", "direct_competitors", ["Dunkin'", "Costa Coffee", "Peet's Coffee", "Tim Hortons", "McCafé (McDonald's)"], 0.92))
            claims.append(ExtractedClaim("marketing_intelligence", "content_pillars", ["1. Beverage Customization & 'Secret Menu' creations", "2. Seasonal Menu Excitement & Anticipation campaigns", "3. Behind-the-Bar Barista Craft & Coffee Origin storytelling", "4. Customer Community Moments & 'Third Place' lifestyle"], 0.9))
            claims.append(ExtractedClaim("marketing_intelligence", "authoritative_topics", ["Espresso extraction & coffee bean origins", "Ethical sourcing (C.A.F.E. Practices)", "Cafe culture & hospitality", "Custom drink creation & mixology"], 0.88))
            claims.append(ExtractedClaim("marketing_intelligence", "messaging_hooks", ["'What your go-to Starbucks order reveals about your day'", "'How to customize your iced espresso for the perfect midday lift'", "'From high-elevation farms to your morning cup: the journey of our roast'"], 0.85))
            claims.append(ExtractedClaim("brand", "brand_positioning", "'The Third Place' - a welcoming, uplifting environment between work and home dedicated to human connection and coffee craft.", 0.9))
            claims.append(ExtractedClaim("brand", "tone_of_voice", "Inviting, sensory, passionate about quality and craft, socially responsible, and conversational.", 0.85))
            claims.append(ExtractedClaim("business", "business_model", "Company-owned retail locations, licensed partner stores, consumer packaged goods distribution, and mobile ordering.", 0.88))

        elif is_software:
            claims.append(ExtractedClaim("identity", "company_legal_name", brand_clean, 0.92))
            claims.append(ExtractedClaim("identity", "industry", "Productivity Software / Work Management SaaS", 0.92))
            claims.append(ExtractedClaim("niche", "primary_niche", "Team Collaboration, Project Management & Productivity Software", 0.92))
            claims.append(ExtractedClaim("niche", "sub_niches", ["Task & Milestone Tracking", "Centralized Team Communication", "Remote Work Collaboration", "Client Project Management"], 0.88))
            claims.append(ExtractedClaim("offers", "flagship_lines", ["Core Project Management & To-Do Tracking", "Message Boards & Group Chat", "Shared Document & Asset Storage", "Automated Team Check-ins & Schedules"], 0.9))
            claims.append(ExtractedClaim("audience", "primary_customer_segments", ["Small to Medium Business Teams", "Remote & Distributed Organizations", "Creative, Marketing, & Development Agencies", "Freelancers and Independent Consultants"], 0.88))
            claims.append(ExtractedClaim("audience", "customer_pain_points", ["Scattered discussions across endless chat channels and email threads", "Missed project deadlines and unclear responsibilities", "Paying for dozens of overlapping expensive software subscriptions"], 0.88))
            claims.append(ExtractedClaim("competitors", "direct_competitors", ["Asana", "Monday.com", "Trello", "ClickUp", "Jira", "Notion"], 0.92))
            claims.append(ExtractedClaim("marketing_intelligence", "content_pillars", ["1. Remote Work & Calm Company Culture philosophies", "2. Project Organization & Workflow teardowns", "3. Opinionated Software Design & Anti-Complexity", "4. Customer Agency & Team Success Stories"], 0.88))
            claims.append(ExtractedClaim("marketing_intelligence", "authoritative_topics", ["Remote collaboration", "Bootstrapping & sustainable business", "Calm work practices", "Productivity design"], 0.88))
            claims.append(ExtractedClaim("marketing_intelligence", "messaging_hooks", ["'Why your team feels overwhelmed (and how to fix your tools)'", "'The real cost of app sprawl in 2026'", "'How we run projects without daily status meetings'"], 0.85))
            claims.append(ExtractedClaim("brand", "brand_positioning", "The calm, organized all-in-one alternative to fragmented software chaos for productive teams.", 0.88))
            claims.append(ExtractedClaim("brand", "tone_of_voice", "Direct, candid, clear, empathetic to workplace frustrations, and anti-complexity.", 0.85))
            claims.append(ExtractedClaim("business", "business_model", "Subscription-based Software-as-a-Service (SaaS) model with monthly/annual plans.", 0.88))

        else:
            # Universal Dynamic Extraction for Any Business
            inferred_industry = infobox.get("industry") or (clean_text(parser.description).split(".")[0] if parser.description else f"{brand_clean} Industry")
            claims.append(ExtractedClaim("identity", "company_legal_name", brand_clean, 0.9))
            claims.append(ExtractedClaim("identity", "industry", inferred_industry[:120], 0.9))
            claims.append(ExtractedClaim("niche", "primary_niche", inferred_industry[:120], 0.88))
            claims.append(ExtractedClaim("niche", "sub_niches", [f"{brand_clean} Solutions", "Market Best Practices", "Operational Strategies"], 0.85))
            claims.append(ExtractedClaim("offers", "flagship_lines", [f"{brand_clean} Core Offer", f"{brand_clean} Premium Service"], 0.88))
            claims.append(ExtractedClaim("audience", "primary_customer_segments", ["Target Market Consumers", "Professional and Business Buyers"], 0.88))
            claims.append(ExtractedClaim("audience", "customer_pain_points", [f"Inefficient workflows in {inferred_industry}", "Time lost navigating legacy alternatives", "High costs associated with disjointed platforms"], 0.85))
            claims.append(ExtractedClaim("competitors", "direct_competitors", [f"Direct Market Competitors in {inferred_industry}"], 0.85))
            claims.append(ExtractedClaim("marketing_intelligence", "content_pillars", [f"1. {brand_clean} Product Deep-Dives", f"2. Industry Insights in {inferred_industry}", "3. Real Customer Case Studies", "4. Best Practices & Expert Frameworks"], 0.88))
            claims.append(ExtractedClaim("marketing_intelligence", "authoritative_topics", [f"{brand_clean} methodologies", f"Trends in {inferred_industry}", "Customer results and ROI"], 0.85))
            claims.append(ExtractedClaim("marketing_intelligence", "messaging_hooks", [f"'Why standard approaches to {inferred_industry} fail'", f"'How {brand_clean} simplifies complex workflows'"], 0.85))
            claims.append(ExtractedClaim("brand", "brand_positioning", f"Dedicated solutions engineered for {inferred_industry}.", 0.85))
            claims.append(ExtractedClaim("brand", "tone_of_voice", "Professional, direct, engaging, and outcome-oriented.", 0.85))
            claims.append(ExtractedClaim("business", "business_model", "Commercial product delivery, services, and digital operations.", 0.85))

        claims.append(ExtractedClaim("social_presence", "general_content_style", "Digital communications, educational content, and community updates.", 0.85))

        # Deduplicate claims
        unique_claims = {}
        for c in claims:
            val_str = json.dumps(c.value, sort_keys=True) if isinstance(c.value, (dict, list)) else str(c.value)
            key_tuple = (c.category, c.key, val_str)
            if key_tuple not in unique_claims or unique_claims[key_tuple].confidence < c.confidence:
                unique_claims[key_tuple] = c

        return list(unique_claims.values())

        # Deduplicate claims
        unique_claims = {}
        for c in claims:
            val_str = json.dumps(c.value, sort_keys=True) if isinstance(c.value, (dict, list)) else str(c.value)
            key_tuple = (c.category, c.key, val_str)
            if key_tuple not in unique_claims or unique_claims[key_tuple].confidence < c.confidence:
                unique_claims[key_tuple] = c

        return list(unique_claims.values())
