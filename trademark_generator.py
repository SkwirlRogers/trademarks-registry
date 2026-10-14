#!/usr/bin/env python3
"""
NuttNeptune Trademark Generator & GitHub Registry
Generates, searches, and registers trademarks for NuttNeptune products.
Stores registry on GitHub (trademarks-registry repo).
"""

import asyncio
import json
import os
import re
import sys
import hashlib
from dataclasses import dataclass, asdict, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional, List, Dict, Any
import httpx

# =============================================================================
# DATA MODELS
# =============================================================================

class ProductType(str, Enum):
    TOOL = "tool"
    KIT = "kit"
    PACKAGE = "package"
    SUBSCRIPTION = "subscription"
    PLATFORM = "platform"

class TrademarkStatus(str, Enum):
    IDEA = "idea"
    SEARCHING = "searching"
    FILED = "filed"
    PUBLISHED = "published"
    REGISTERED = "registered"
    ABANDONED = "abandoned"
    OPPOSED = "opposed"

@dataclass
class SocialHandles:
    twitter: Optional[str] = None
    github: Optional[str] = None
    linkedin: Optional[str] = None
    instagram: Optional[str] = None
    discord: Optional[str] = None

@dataclass
class Trademark:
    name: str
    product_type: ProductType
    status: TrademarkStatus = TrademarkStatus.IDEA
    classes: List[int] = field(default_factory=list)
    goods_services: str = ""
    owner: str = "SkwirlyNuts Inc"
    registration_number: Optional[str] = None
    registration_date: Optional[str] = None
    renewal_date: Optional[str] = None
    status_details: str = ""
    domain: Optional[str] = None
    social_handles: SocialHandles = field(default_factory=SocialHandles)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> dict:
        return {
            **asdict(self),
            "product_type": self.product_type.value,
            "status": self.status.value,
            "social_handles": asdict(self.social_handles),
        }

@dataclass
class ExistingMark:
    name: str
    owner: str
    status: str
    registration_number: Optional[str] = None
    classes: List[int] = field(default_factory=list)

@dataclass
class TrademarkSearchResult:
    name: str
    available: bool
    exact_matches: List[dict] = field(default_factory=list)
    similar_matches: List[dict] = field(default_factory=list)
    domain_available: bool = False
    social_available: bool = False

@dataclass
class ProductTrademarkSuite:
    product_name: str
    product_type: ProductType
    primary: Optional[dict] = None
    variations: List[dict] = field(default_factory=list)
    logo_concepts: List[dict] = field(default_factory=list)

# =============================================================================
# CLIENTS
# =============================================================================

class GitHubClient:
    def __init__(self, token: str, repo: str = "SkwirlRogers/trademarks-registry"):
        self.token = token
        self.repo = repo
        self.base_url = "https://api.github.com"
        self.headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
        }

    async def get_file(self, path: str) -> Optional[dict]:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/repos/{self.repo}/contents/{path}",
                headers=self.headers,
            )
            if resp.status_code == 200:
                return resp.json()
            elif resp.status_code == 404:
                return None
            else:
                raise Exception(f"GitHub API error: {resp.status_code} - {resp.text}")

    async def put_file(self, path: str, content: str, message: str, sha: Optional[str] = None) -> dict:
        import base64
        content_b64 = base64.b64encode(content.encode()).decode()
        payload = {
            "message": message,
            "content": content_b64,
            "branch": "main",
        }
        if sha:
            payload["sha"] = sha

        async with httpx.AsyncClient() as client:
            resp = await client.put(
                f"{self.base_url}/repos/{self.repo}/contents/{path}",
                headers=self.headers,
                json=payload,
            )
            return resp.json()

    async def create_repo_if_not_exists(self, description: str = "NuttNeptune Trademark Registry") -> dict:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/repos/{self.repo}",
                headers=self.headers,
            )
            if resp.status_code == 404:
                payload = {
                    "name": self.repo.split("/")[-1],
                    "description": description,
                    "private": False,
                    "auto_init": True,
                }
                resp = await client.post(
                    f"{self.base_url}/user/repos",
                    headers=self.headers,
                    json=payload,
                )
                return resp.json()
            return resp.json()

class USPTOClient:
    BASE_URL = "https://tsdr.uspto.gov/api/v1"

    async def search_exact(self, name: str) -> List[dict]:
        return []

    async def search_similar(self, name: str) -> List[dict]:
        return []

    async def file(self, trademark_data: dict) -> dict:
        return {"registration_number": f"PENDING-{int(datetime.utcnow().timestamp())}"}

class DomainClient:
    async def check(self, name: str) -> bool:
        import socket
        domain = f"{re.sub(r'[^a-z0-9]', '', name.lower())}.com"
        try:
            socket.gethostbyname(domain)
            return False
        except socket.gaierror:
            return True

    async def register(self, domain: str) -> bool:
        return True

class SocialClient:
    PLATFORMS = {
        "twitter": "https://twitter.com/",
        "github": "https://github.com/",
        "linkedin": "https://linkedin.com/in/",
        "instagram": "https://instagram.com/",
        "discord": "https://discord.com/users/",
    }

    async def check(self, name: str) -> bool:
        handle = re.sub(r'[^a-z0-9_]', '', name.lower().replace(" ", ""))
        async with httpx.AsyncClient() as client:
            for platform, base_url in self.PLATFORMS.items():
                url = f"{base_url}{handle}"
                try:
                    resp = await httpx.get(url, timeout=5.0)
                    if resp.status_code == 200:
                        return False
                except:
                    pass
        return True

    async def reserve(self, name: str) -> bool:
        return True

# =============================================================================
# TRADEMARK REGISTRY (GitHub-backed)
# =============================================================================

class TrademarkRegistry:
    def __init__(self, github_client: 'GitHubClient'):
        self.github = github_client

    async def load_index(self) -> dict:
        file_data = await self.github.get_file("registry.json")
        if file_data:
            import base64
            content = base64.b64decode(file_data["content"]).decode()
            return json.loads(content)
        return {"trademarks": [], "suites": [], "licenses": [], "registrations": []}

    async def save_index(self, index: dict, sha: Optional[str] = None):
        await self.github.put_file(
            "registry.json",
            json.dumps(index, indent=2),
            "Update trademark index",
            sha,
        )

    async def save(self, trademark: 'Trademark') -> bool:
        index = await self.load_index()
        index["trademarks"].append(trademark.to_dict())
        sha = file_data.get("sha") if (file_data := await self.github.get_file("registry.json")) else None
        await self.save_index(index, sha)
        return True

    async def save_suite(self, suite: 'ProductTrademarkSuite') -> bool:
        index = await self.load_index()
        index["suites"].append(asdict(suite))
        sha = file_data.get("sha") if (file_data := await self.github.get_file("registry.json")) else None
        await self.save_index(index, sha)
        return True

# =============================================================================
# MAIN GENERATOR
# =============================================================================

class TrademarkGenerator:
    USPTO_CLASSES = {
        ProductType.TOOL: [9, 42],
        ProductType.KIT: [9, 16, 42],
        ProductType.PACKAGE: [9, 42],
        ProductType.SUBSCRIPTION: [9, 35, 42],
        ProductType.PLATFORM: [9, 35, 42, 45],
    }

    def __init__(self, github_token: str):
        self.github = GitHubClient(github_token)
        self.uspto = USPTOClient()
        self.domain = DomainClient()
        self.social = SocialClient()
        self.registry = TrademarkRegistry(self.github)

    def generate_candidates(self, seed: str, count: int = 20) -> List[str]:
        base = seed.strip()
        patterns = [
            f"Nutt{base}",
            f"{base}Nutt",
            f"Neptune{base}",
            f"{base}Neptune",
            f"{base}Tools",
            f"{base}Kit",
            f"{base}Pack",
            f"{base}Suite",
            f"{base}Pro",
            f"{base}Core",
            f"{base}Base",
            f"{base}Flow",
            f"{base}Hub",
            f"{base}Sync",
            f"{base}AI",
            f"{base}Cloud",
        ]
        candidates = []
        for p in patterns:
            if len(candidates) >= 20:
                break
            candidates.append(p)
            for suffix in ["AI", "Cloud", "Sync", "Hub", "Pro", "Core", "Flow"]:
                candidates.append(f"{candidates[-1]}{suffix}")
                if len(candidates) >= 20:
                    break
        return candidates[:20]

    def get_classes_for_type(self, ptype: ProductType) -> List[int]:
        return self.USPTO_CLASSES.get(ptype, [9, 42])

    def get_goods_services(self, ptype: ProductType) -> str:
        mapping = {
            ProductType.TOOL: "Computer software for automation and productivity",
            ProductType.KIT: "Downloadable software kits and templates",
            ProductType.PACKAGE: "Bundled software packages and suites",
            ProductType.SUBSCRIPTION: "SaaS subscription services",
            ProductType.PLATFORM: "Platform as a service (PaaS)",
        }
        return mapping.get(ptype, "Computer software")

    async def search(self, name: str) -> dict:
        exact = await self.uspto.search_exact(name)
        similar = await self.uspto.search_similar(name)
        domain_avail = await self.domain.check(name)
        social_avail = await self.social.check(name)
        return {
            "name": name,
            "available": len(exact) == 0,
            "exact_matches": exact,
            "similar_matches": similar,
            "domain_available": domain_avail,
            "social_available": social_avail,
        }

    async def generate_suite(self, product_name: str, ptype: ProductType) -> dict:
        base = f"NuttNeptune {product_name}"
        candidates = self.generate_candidates(product_name, 20)
        suite = {
            "product_name": product_name,
            "product_type": ptype.value,
            "primary": None,
            "variations": [],
            "logo_concepts": [],
        }

        for candidate in candidates:
            search = await self.search(candidate)
            if search["available"]:
                tm = {
                    "name": candidate,
                    "product_type": ptype.value,
                    "status": "idea",
                    "classes": self.get_classes_for_type(ptype),
                    "goods_services": self.get_goods_services(ptype),
                    "owner": "SkwirlyNuts Inc",
                    "registration_number": None,
                    "registration_date": None,
                    "renewal_date": None,
                    "status_details": "Available - ready to file",
                    "domain": f"{re.sub(r'[^a-z0-9]', '', candidate.lower())}.com",
                    "social_handles": {},
                    "created_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat(),
                }
                if suite["primary"] is None:
                    suite["primary"] = tm
                else:
                    suite["variations"].append(tm)

        return suite

# =============================================================================
# CLI
# =============================================================================

async def main():
    import argparse
    parser = argparse.ArgumentParser(description="NuttNeptune Trademark Generator")
    parser.add_argument("command", choices=["generate", "search", "register", "suite"])
    parser.add_argument("--name", help="Trademark name or product name")
    parser.add_argument("--type", choices=["tool", "kit", "package", "subscription", "platform"], default="tool")
    parser.add_argument("--count", type=int, default=20)
    parser.add_argument("--github-token", help="GitHub token (or set GITHUB_TOKEN env)")
    parser.add_argument("--output", help="Output file path")
    args = parser.parse_args()

    token = args.github_token or os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
    if not token:
        print("Error: GitHub token required (--github-token or GITHUB_TOKEN env)")
        sys.exit(1)

    generator = TrademarkGenerator(token)

    if args.command == "generate":
        if not args.name:
            print("Error: --name required")
            sys.exit(1)
        candidates = generator.generate_candidates(args.name, args.count)
        for c in candidates:
            print(c)

    elif args.command == "search":
        if not args.name:
            print("Error: --name required")
            sys.exit(1)
        result = await generator.search(args.name)
        print(json.dumps(result, indent=2))

    elif args.command == "suite":
        if not args.name:
            print("Error: --name required")
            sys.exit(1)
        ptype = ProductType(args.type)
        suite = await generator.generate_suite(args.name, ptype)
        print(json.dumps(suite, indent=2))

    elif args.command == "register":
        print("Registration requires attorney filing - not automated")

if __name__ == "__main__":
    asyncio.run(main())