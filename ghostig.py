import argparse
import textwrap
from dataclasses import asdict, dataclass
from json import JSONDecodeError, dumps
from typing import Any, Dict, Optional
from urllib.parse import quote_plus

import requests
from requests import Session
from requests.exceptions import RequestException

try:  # Optional enrichment dependency
    import phonenumbers
    from phonenumbers.phonenumberutil import NumberParseException, region_code_for_country_code
except ImportError:  # pragma: no cover - fallback when lib missing
    phonenumbers = None

    class NumberParseException(Exception):
        """Fallback exception when phonenumbers is unavailable."""

    def region_code_for_country_code(_: int) -> Optional[str]:
        return None

try:  # Optional enrichment dependency
    import pycountry
except ImportError:  # pragma: no cover
    pycountry = None


WEB_PROFILE_URL = "https://i.instagram.com/api/v1/users/web_profile_info/"
USER_INFO_URL = "https://i.instagram.com/api/v1/users/{user_id}/info/"
LOOKUP_URL = "https://i.instagram.com/api/v1/users/lookup/"

WEB_PROFILE_HEADERS = {
    "User-Agent": "iphone_ua",
    "x-ig-app-id": "936619743392459",
}
USER_INFO_HEADERS = {
    "User-Agent": "Instagram 64.0.0.14.96",
}
LOOKUP_HEADERS = {
    "Accept-Language": "en-US",
    "User-Agent": "Instagram 101.0.0.15.120",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "X-IG-App-ID": "124024574287414",
    "Accept-Encoding": "gzip, deflate",
    "Host": "i.instagram.com",
    "Connection": "keep-alive",
}
DEFAULT_TIMEOUT = 15


class InstagramAPIError(RuntimeError):
    """Base error for Instagram API interactions."""


class NotFoundError(InstagramAPIError):
    """Raised when a user cannot be found."""


class RateLimitError(InstagramAPIError):
    """Raised when Instagram returns a rate-limit response."""


class InvalidInputError(InstagramAPIError):
    """Raised when the CLI receives invalid input."""


@dataclass
class UserProfile:
    username: str
    user_id: str
    full_name: str
    is_verified: bool
    is_business: bool
    is_private: bool
    follower_count: int
    following_count: int
    media_count: int
    total_igtv_videos: int
    biography: str
    external_url: Optional[str]
    is_whatsapp_linked: bool
    is_memorialized: bool
    is_new_to_instagram: bool
    public_email: Optional[str]
    public_phone_country_code: Optional[str]
    public_phone_number: Optional[str]
    hd_profile_pic_url: Optional[str]

    @classmethod
    def from_payload(cls, payload: Dict[str, Any], user_id: str) -> "UserProfile":
        return cls(
            username=payload.get("username", ""),
            user_id=user_id,
            full_name=payload.get("full_name") or "-",
            is_verified=payload.get("is_verified", False),
            is_business=payload.get("is_business", False),
            is_private=payload.get("is_private", False),
            follower_count=payload.get("follower_count", 0),
            following_count=payload.get("following_count", 0),
            media_count=payload.get("media_count", 0),
            total_igtv_videos=payload.get("total_igtv_videos", 0),
            biography=payload.get("biography") or "",
            external_url=payload.get("external_url"),
            is_whatsapp_linked=payload.get("is_whatsapp_linked", False),
            is_memorialized=payload.get("is_memorialized", False),
            is_new_to_instagram=payload.get("is_new_to_instagram", False),
            public_email=payload.get("public_email"),
            public_phone_country_code=payload.get("public_phone_country_code"),
            public_phone_number=payload.get("public_phone_number"),
            hd_profile_pic_url=(payload.get("hd_profile_pic_url_info") or {}).get("url"),
        )


@dataclass
class LookupInsight:
    message: Optional[str]
    obfuscated_email: Optional[str]
    obfuscated_phone: Optional[str]

    @classmethod
    def from_payload(cls, payload: Dict[str, Any]) -> "LookupInsight":
        return cls(
            message=payload.get("message"),
            obfuscated_email=payload.get("obfuscated_email"),
            obfuscated_phone=payload.get("obfuscated_phone"),
        )

    def has_data(self) -> bool:
        return any([self.message, self.obfuscated_email, self.obfuscated_phone])


class InstagramClient:
    def __init__(self, session_id: str, timeout: int = DEFAULT_TIMEOUT):
        if not session_id:
            raise InvalidInputError("A session ID is required.")
        self.session: Session = Session()
        self.session.cookies.set("sessionid", session_id)
        self.timeout = timeout

    def get_profile(self, search: str, search_type: str) -> UserProfile:
        if search_type == "username":
            user_id = self._fetch_user_id(search)
        else:
            user_id = self._normalize_user_id(search)

        return self._fetch_profile_by_id(user_id)

    def advanced_lookup(self, username: str) -> LookupInsight:
        signed_body = "signed_body=SIGNATURE." + quote_plus(
            dumps({"q": username, "skip_recovery": "1"}, separators=(",", ":"))
        )
        payload = self._request(
            "POST",
            LOOKUP_URL,
            headers=LOOKUP_HEADERS,
            data=signed_body,
        )
        return LookupInsight.from_payload(payload)

    def _fetch_user_id(self, username: str) -> str:
        if not username:
            raise InvalidInputError("Username cannot be empty.")
        payload = self._request(
            "GET",
            f"{WEB_PROFILE_URL}?username={username}",
            headers=WEB_PROFILE_HEADERS,
        )
        try:
            return payload["data"]["user"]["id"]
        except KeyError as exc:
            raise InstagramAPIError("Unexpected response: missing user id.") from exc

    def _fetch_profile_by_id(self, user_id: str) -> UserProfile:
        payload = self._request(
            "GET",
            USER_INFO_URL.format(user_id=user_id),
            headers=USER_INFO_HEADERS,
        )
        user_data = payload.get("user")
        if not user_data:
            raise InstagramAPIError("Instagram did not return user data.")
        return UserProfile.from_payload(user_data, user_id)

    def _normalize_user_id(self, user_id: str) -> str:
        try:
            return str(int(user_id))
        except (TypeError, ValueError) as exc:
            raise InvalidInputError("User ID must be numeric.") from exc

    def _request(self, method: str, url: str, *, headers: Dict[str, str], data: Optional[str] = None) -> Dict[str, Any]:
        try:
            response = self.session.request(
                method,
                url,
                headers=headers,
                data=data,
                timeout=self.timeout,
            )
        except RequestException as exc:
            raise InstagramAPIError("Unable to reach Instagram. Check your connection.") from exc

        if response.status_code == 404:
            raise NotFoundError("User not found.")
        if response.status_code == 429:
            raise RateLimitError("Instagram rate limit reached. Try again later.")
        if response.status_code >= 400:
            raise InstagramAPIError(f"Instagram returned HTTP {response.status_code}.")

        if not response.content:
            return {}

        try:
            return response.json()
        except JSONDecodeError as exc:
            raise InstagramAPIError("Instagram responded with invalid JSON.") from exc


def bool_label(value: bool) -> str:
    return "Yes" if value else "No"


def format_phone(country_code: Optional[str], number: Optional[str]) -> Optional[str]:
    if not country_code or not number:
        return None
    raw = f"+{country_code} {number}"
    try:
        parsed = phonenumbers.parse(raw)
        iso = region_code_for_country_code(parsed.country_code)
        country = pycountry.countries.get(alpha_2=iso) if iso else None
        country_name = country.name if country else "Unknown country"
        return f"{raw} ({country_name})"
    except (NumberParseException, AttributeError, KeyError):
        return raw


def render_rows(rows: Dict[str, Optional[str]]) -> str:
    filtered = {k: v for k, v in rows.items() if v not in (None, "", [])}
    if not filtered:
        return ""
    width = max(len(key) for key in filtered)
    return "\n".join(f"{key:<{width}} : {value}" for key, value in filtered.items())


def format_biography(text: str) -> str:
    if not text:
        return "  -"
    return textwrap.indent(text.strip(), "  ")


def print_profile(profile: UserProfile, lookup: Optional[LookupInsight]) -> None:
    rows = {
        "Username": profile.username,
        "User ID": profile.user_id,
        "Full Name": profile.full_name,
        "Verified": bool_label(profile.is_verified),
        "Business Account": bool_label(profile.is_business),
        "Private Account": bool_label(profile.is_private),
        "Followers": f"{profile.follower_count:,}",
        "Following": f"{profile.following_count:,}",
        "Posts": f"{profile.media_count:,}",
        "IGTV Videos": f"{profile.total_igtv_videos:,}",
        "External URL": profile.external_url,
        "WhatsApp Linked": bool_label(profile.is_whatsapp_linked),
        "Memorial Account": bool_label(profile.is_memorialized),
        "New to Instagram": bool_label(profile.is_new_to_instagram),
        "Public Email": profile.public_email,
        "Public Phone": format_phone(profile.public_phone_country_code, profile.public_phone_number),
        "Profile Picture": profile.hd_profile_pic_url,
    }

    if lookup and lookup.has_data():
        rows["Lookup Message"] = lookup.message
        rows["Obfuscated Email"] = lookup.obfuscated_email
        rows["Obfuscated Phone"] = lookup.obfuscated_phone

    print("=" * 60)
    print("INSTAGRAM PROFILE INSIGHTS")
    print("=" * 60)
    print(render_rows(rows))
    print("\nBiography:")
    print(format_biography(profile.biography))
    print("=" * 60)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Lightweight Instagram OSINT helper. Provide a session id and a username or numeric id."
    )
    parser.add_argument("-s", "--sessionid", required=True, help="Instagram session ID cookie value.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-u", "--username", help="Instagram username to inspect.")
    group.add_argument("-i", "--id", help="Numeric Instagram user ID to inspect.")
    parser.add_argument(
        "--skip-lookup",
        action="store_true",
        help="Skip the secondary lookup request (avoids extra API traffic).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the collected data as formatted JSON instead of human-readable text.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    client = InstagramClient(args.sessionid)
    search_type = "id" if args.id else "username"
    search_value = args.id or args.username

    try:
        profile = client.get_profile(search_value, search_type)
        lookup = None if args.skip_lookup else client.advanced_lookup(profile.username)
    except InstagramAPIError as exc:
        raise SystemExit(str(exc)) from exc

    if args.json:
        payload = {
            "profile": asdict(profile),
            "lookup": asdict(lookup) if lookup else None,
        }
        print(dumps(payload, indent=2))
        return

    print_profile(profile, lookup)


if __name__ == "__main__":
    main()

