#!/usr/bin/env python3
"""
NuttNeptune Trademark Registry - GitHub Storage Module
Stores trademark registry, licenses, and registrations on GitHub.
"""

import os
import json
import re
import base64
import hashlib
from datetime import datetime
from typing import Optional, List, Dict, Any
import httpx

class GitHubStorage:
    """GitHub-backed storage for trademark registry."""

    def __init__(self, token: str, repo: str = "SkwirlRogers/trademarks-registry"):
        self.token = token
        self.repo = repo
        self.base_url = "https://api.github.com"
        self.headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "NuttNeptune-TrademarkRegistry",
        }
        self.repo_owner, self.repo_name = repo.split("/")

    async def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        url = f"{self.base_url}/repos/{self.repo}{path}"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.request(method, url, headers=self.headers, **kwargs)
            return resp

    async def ensure_repo_exists(self, description: str = "NuttNeptune Trademark Registry") -> bool:
        """Create repo if it doesn't exist."""
        resp = await self._request("GET", "")
        if resp.status_code == 404:
            resp = await self._request("POST", "/user/repos", json={
                "name": self.repo.split("/")[-1],
                "description": "NuttNeptune Trademark Registry - trademarks, licenses, registrations",
                "private": False,
                "auto_init": True,
            })
            return resp.status_code == 201
        return True

    async def get_file(self, path: str) -> Optional[Dict]:
        resp = await self._request("GET", f"/contents/{path}")
        if resp.status_code == 200:
            data = resp.json()
            if data.get("encoding") == "base64":
                content = base64.b64decode(data["content"]).decode()
                return {
                    "content": json.loads(content) if data["name"].endswith(".json") else data["content"],
                    "sha": data["sha"],
                    "path": data["path"],
                }
        return None

    async def put_file(self, path: str, content: str, message: str, sha: Optional[str] = None) -> bool:
        content_b64 = base64.b64encode(content.encode()).decode()
        payload = {
            "message": message,
            "content": content_b64,
            "branch": "main",
        }
        if sha:
            payload["sha"] = sha

        resp = await self._request("PUT", f"/contents/{path}", json=payload)
        return resp.status_code in (200, 201)

    async def get_file_sha(self, path: str) -> Optional[str]:
        file_data = await self.get_file(path)
        return file_data.get("sha") if file_data else None

    # =========================================================================
    # TRADEMARK REGISTRY OPERATIONS
    # =========================================================================

    async def load_registry(self) -> dict:
        data = await self.get_file("registry.json")
        if data:
            return data["content"]
        return {"trademarks": [], "suites": [], "licenses": [], "registrations": []}

    async def save_registry(self, registry: dict) -> bool:
        sha = await self.get_file_sha("registry.json")
        return await self.put_file("registry.json", json.dumps(registry, indent=2, sort_keys=True), "Update trademark registry", sha)

    async def save_trademark(self, trademark: dict) -> bool:
        registry = await self.load_registry()
        existing_idx = next((i for i, t in enumerate(registry["trademarks"]) if t["name"] == trademark["name"]), None)
        if existing_idx is not None:
            registry["trademarks"][existing_idx] = trademark
        else:
            registry["trademarks"].append(trademark)
        return await self.save_registry(registry)

    async def save_suite(self, suite: dict) -> bool:
        registry = await self.load_registry()
        registry["suites"].append(suite)
        return await self.save_registry(registry)

    async def save_license(self, license_data: dict) -> bool:
        registry = await self.load_registry()
        registry["licenses"].append(license_data)
        return await self.save_registry(registry)

    async def save_registration(self, registration: dict) -> bool:
        registry = await self.load_registry()
        registry["registrations"].append(registration)
        return await self.save_registry(registry)

    async def get_trademark(self, name: str) -> Optional[dict]:
        registry = await self.load_registry()
        return next((t for t in registry["trademarks"] if t["name"].lower() == name.lower()), None)

    async def search_trademarks(self, query: str) -> List[dict]:
        registry = await self.load_registry()
        query = query.lower()
        return [t for t in registry["trademarks"] if query in t["name"].lower()]

    # =========================================================================
    # LICENSE MANAGEMENT
    # =========================================================================

    async def create_license(self, license_data: dict) -> dict:
        license_data.setdefault("id", hashlib.sha256(f"{license_data['product']}{datetime.utcnow().isoformat()}".encode()).hexdigest()[:16])
        license_data.setdefault("created_at", datetime.utcnow().isoformat())
        license_data.setdefault("status", "active")
        await self.save_license(license_data)
        return license_data

    async def validate_license(self, license_id: str, machine_fingerprint: str) -> dict:
        registry = await self.load_registry()
        license_data = next((l for l in registry["licenses"] if l["id"] == license_id), None)
        if not license_data:
            return {"valid": False, "error": "License not found"}
        if license_data["status"] != "active":
            return {"valid": False, "error": "License not active"}
        allowed = license_data.get("allowed_machines", [])
        if machine_fingerprint not in allowed and allowed:
            return {"valid": False, "error": "Machine not authorized"}
        return {"valid": True, "license": license_data}

    # =========================================================================
    # REGISTRATION MANAGEMENT
    # =========================================================================

    async def create_registration(self, registration: dict) -> dict:
        registration.setdefault("id", hashlib.sha256(f"{registration['trademark']}{datetime.utcnow().isoformat()}".encode()).hexdigest()[:16])
        registration.setdefault("created_at", datetime.utcnow().isoformat())
        registration.setdefault("status", "pending")
        await self.save_registration(registration)
        return registration

    async def update_registration_status(self, registration_id: str, status: str, details: str = "") -> bool:
        registry = await self.load_registry()
        for reg in registry["registrations"]:
            if reg["id"] == registration_id:
                reg["status"] = status
                reg["status_details"] = details
                reg["updated_at"] = datetime.utcnow().isoformat()
                return await self.save_registry(registry)
        return False


def slugify(text: str) -> str:
    """Convert text to URL-safe slug."""
    return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')


async def main():
    import argparse
    parser = argparse.ArgumentParser(description="NuttNeptune Trademark Registry - GitHub Storage")
    parser.add_argument("command", choices=["init", "search", "add", "license", "validate", "register", "sync"])
    parser.add_argument("--name", help="Trademark name")
    parser.add_argument("--product", help="Product name")
    parser.add_argument("--type", choices=["tool", "kit", "package", "subscription", "platform"], default="tool")
    parser.add_argument("--license-id", help="License ID")
    parser.add_argument("--machine", help="Machine fingerprint")
    parser.add_argument("--github-token", help="GitHub token (or set GITHUB_TOKEN env)")
    parser.add_argument("--output", help="Output file")
    args = parser.parse_args()

    token = args.github_token or os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
    if not token:
        print("Error: GitHub token required (--github-token or GITHUB_TOKEN env)")
        sys.exit(1)

    storage = GitHubStorage(token)
    await storage.ensure_repo_exists()

    if args.command == "init":
        print("Repository initialized")
    elif args.command == "search":
        if not args.name:
            print("Error: --name required")
            sys.exit(1)
        results = await storage.search_trademarks(args.name)
        print(json.dumps(results, indent=2))
    elif args.command == "add":
        print("Add trademark - use trademark_generator.py instead")
    elif args.command == "license":
        if not args.name or not args.product:
            print("Error: --name and --product required")
            sys.exit(1)
        license_data = {
            "product": args.product,
            "type": "subscription" if "subscription" in args.type else "perpetual",
            "features": ["all"],
        }
        license_data = await storage.create_license(license_data)
        print(json.dumps(license_data, indent=2))
    elif args.command == "validate":
        if not args.license_id or not args.machine:
            print("Error: --license-id and --machine required")
            sys.exit(1)
        result = await storage.validate_license(args.license_id, args.machine)
        print(json.dumps(result, indent=2))
    elif args.command == "register":
        print("Registration - use trademark_generator.py")
    elif args.command == "sync":
        print("Syncing registry...")
        registry = await storage.load_registry()
        print(f"Total trademarks: {len(registry['trademarks'])}")
        print(f"Total suites: {len(registry['suites'])}")
        print(f"Total licenses: {len(registry['licenses'])}")
        print(f"Total registrations: {len(registry['registrations'])}")


if __name__ == "__main__":
    asyncio.run(main())