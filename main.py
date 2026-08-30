import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, Dict, Any, List
from pathlib import Path
from io import BytesIO
from urllib.parse import quote
import primp
from colorama import Fore, Style
from PIL import Image
import asyncio
import websockets
from python_socks.async_.asyncio import Proxy
import requests
from stealth_requests import StealthSession
import base64
import json
import os
import platform
import random
import re
import string
import threading
import time
import uuid
import websocket
import subprocess
import sys
import imaplib
import email
from datetime import datetime
from urllib.parse import urlparse
import warnings
from urllib3.exceptions import InsecureRequestWarning
warnings.simplefilter('ignore', InsecureRequestWarning)

P = "\033[38;2;121;3;255m"
C = "\033[38;2;0;255;220m"
G = "\033[38;2;0;255;136m"
Y = "\033[38;2;255;200;0m"
D = "\033[38;2;100;100;110m"
W = "\033[97m"
RD = "\033[38;2;255;50;80m"
R = "\033[0m"
UP = "\033[38;2;180;0;255m"
OR = "\033[38;2;255;140;0m"                  
class APZMailApi:
    BASE_URL = "https://api.cybertemp.xyz"
    def __init__(self, logger=None, forced_domain: str = None, api_key: str = None):
        self.created_emails = {}
        self.logger = logger
        self.forced_domain = forced_domain
        self.api_key = (api_key or os.getenv("CYBERTEMP_API_KEY", "")).strip()
        if not self.api_key:
            self.api_key = self._read_api_key_from_config()
        self.headers = {"X-API-KEY": self.api_key} if self.api_key else {}
    def _build_proxies(self, proxy: str = None):
        if not proxy:
            return None
        parsed = parse_proxy(proxy)
        return {"http": parsed, "https": parsed} if parsed else None
    def _log(self, message: str):
        pass
    def _read_api_key_from_config(self):
        try:
            with open("config.json", "r", encoding="utf-8") as f:
                cfg = json.load(f)
            return (cfg.get("mail_services", {}).get("cybertemp", {}).get("api_key") or "").strip()
        except Exception:
            return ""
    def get_domains(self):
        try:
            with open("config.json", "r", encoding="utf-8") as f:
                cfg = json.load(f)
            cybertemp_cfg = cfg.get("mail_services", {}).get("cybertemp", {})
            if "domains" in cybertemp_cfg and isinstance(cybertemp_cfg["domains"], list) and len(cybertemp_cfg["domains"]) > 0:
                return cybertemp_cfg["domains"]
        except Exception:
            pass

        try:
            resp = requests.get(f"{self.BASE_URL}/getDomains", params={"type": "discord"}, headers=self.headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, dict) and "domains" in data:
                    domains_list = data["domains"]
                elif isinstance(data, list):
                    domains_list = data
                else:
                    return []
                return [d.get("domain", d) if isinstance(d, dict) else d for d in domains_list]
        except:
            pass
        return []
    def create_account(self, email: str = None, password: str = None, proxy: str = None):
        if email and '@' in email:
            created_email = email
        elif self.forced_domain:
            local = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
            created_email = f"{local}@{self.forced_domain}"
        else:
            domains = self.get_domains()
            if not domains:
                domains = ["randommail.com"] 
            target_domain = random.choice(domains)
            username = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
            created_email = f"{username}@{target_domain}"
        if not created_email:
            self._log("APZMail could not create an email")
            return None
        self.created_emails[created_email] = password or ""
        self._log(f"Prepared email: {created_email}")
        return created_email
    def get_verify_url(self, email: str, poll_interval: int = 3, timeout: int = 120, proxy: str = None):
        start_time = time.time()
        used_message_ids = set()
        while time.time() - start_time < timeout:
            try:
                resp = requests.get(f"{self.BASE_URL}/getMail", params={"email": email}, headers=self.headers, timeout=10)
                if resp.status_code == 200:
                    messages = resp.json()
                    if isinstance(messages, list) and messages:
                        for msg in messages:
                            msg_id = msg.get("id")
                            if msg_id in used_message_ids:
                                continue
                            subject = msg.get("subject", "")
                            if "discord" in subject.lower() or "verify" in subject.lower() or "verif" in subject.lower():
                                html_body = msg.get("html", "") or msg.get("text", "") or ""
                                text_body = msg.get("text", "") or ""
                                combined = html_body + text_body
                                all_links = re.findall(r'https?://[^\s"\'<>]+', combined)
                                target_links = [l for l in all_links if ("discord.com" in l or "click.discord.com" in l) and "support." not in l and "blog." not in l]
                                if target_links:
                                    url = None
                                    if len(target_links) >= 2:
                                        second_url = target_links[1]
                                        if "verify" in second_url.lower() or "token=" in second_url.lower() or "click.discord.com" in second_url:
                                            url = second_url
                                    if not url:
                                        url = max(target_links, key=len)
                                    if "click.discord.com" in url:
                                        resolved = self._resolve_url(url, proxy=proxy)
                                        if resolved:
                                            return resolved
                                    return url
                                used_message_ids.add(msg_id)
            except Exception as e:
                self._log(f"Error reading inbox: {e}")
            time.sleep(poll_interval)
        self._log(f"Timeout waiting for verify URL in {email}")
        return None
    def _resolve_url(self, url: str, proxy: str = None) -> str:
        proxies = self._build_proxies(proxy)
        try:
            resp = requests.head(url, allow_redirects=True, timeout=10, proxies=proxies)
            final_url = resp.url
            if "discord.com/verify" in final_url:
                return final_url
        except Exception:
            pass
        return None
class DuckMailAPI:
    BASE_URL = "https://api.duckmail.sbs"
    def __init__(self, password: str = ""):
        self.password = password or ''.join(random.choices(string.ascii_letters + string.digits, k=14))
        self.s = requests.Session()
        self.s.headers.update({"Content-Type": "application/json"})
        self._bearer = None
        self._email = None
    def _domain(self) -> str:
        try:
            r = self.s.get(f"{self.BASE_URL}/domains", timeout=10)
            if r.status_code == 200:
                for m in r.json().get("hydra:member", []):
                    if m.get("ownerId") is None:
                        return m["domain"]
        except:
            pass
        return "duckmail.sbs"
    def create_account(self, email: str = None, password: str = None, proxy: str = None):
        domain = self._domain()
        addr = f"{''.join(random.choices(string.ascii_lowercase + string.digits, k=10))}@{domain}"
        pw = self.password
        r = self.s.post(f"{self.BASE_URL}/accounts", json={"address": addr, "password": pw, "expiresIn": 0}, timeout=10)
        if r.status_code != 201:
            return None
        token_r = self.s.post(f"{self.BASE_URL}/token", json={"address": addr, "password": pw}, timeout=10)
        if token_r.status_code != 200:
            return None
        self._bearer = token_r.json().get("token")
        self._email = addr
        return addr
    def get_verify_url(self, email: str, poll_interval: int = 5, timeout: int = 120, proxy: str = None):
        if not self._bearer:
            return None
        headers = {"Authorization": f"Bearer {self._bearer}"}
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                r = self.s.get(f"{self.BASE_URL}/messages", headers=headers, timeout=10)
                if r.status_code == 200:
                    for msg in r.json().get("hydra:member", []):
                        subj = (msg.get("subject", "") or "").lower()
                        sender = (msg.get("from", {}) or {}).get("address", "").lower()
                        if "verify" in subj or "discord" in sender or "noreply@discord" in sender:
                            detail = self.s.get(f"{self.BASE_URL}/messages/{msg['id']}", headers=headers, timeout=10).json()
                            body = detail.get("text", "") or " ".join(detail.get("html", ""))
                            for pat in [r'https://discord\.com/verify/[^\s"\'<>]+',
                                        r'https://discord\.com/verify\?token=[^\s"\'<>]+',
                                        r'https://click\.discord\.com/[^\s"\'<>]+']:
                                m = re.search(pat, body, re.IGNORECASE)
                                if m:
                                    link = m.group(0).replace("&amp;", "&")
                                    self.s.delete(f"{self.BASE_URL}/messages/{msg['id']}", headers=headers)
                                    return link
            except:
                pass
            time.sleep(poll_interval)
        return None

class TempMailLolAPI:
    BASE_URL = "https://api.tempmail.lol"
    def __init__(self):
        self._token = None
    def create_account(self, email: str = None, password: str = None, proxy: str = None):
        try:
            r = requests.get(f"{self.BASE_URL}/generate", timeout=10)
            if r.status_code == 200:
                data = r.json()
                self._token = data.get("token", "")
                return data.get("address", "")
        except:
            pass
        return None
    def get_verify_url(self, email: str, poll_interval: int = 5, timeout: int = 120, proxy: str = None):
        if not self._token:
            return None
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                r = requests.get(f"{self.BASE_URL}/auth/{self._token}", timeout=10)
                if r.status_code == 200:
                    data = r.json()
                    for msg in data.get("email", []):
                        subject = msg.get("subject", "")
                        body = msg.get("body", "") or msg.get("html", "")
                        if "discord" in subject.lower() or "verify" in subject.lower():
                            all_links = re.findall(r'https?://[^\s"\'<>]+', body)
                            target_links = [l for l in all_links if ("discord.com" in l or "click.discord.com" in l) and "support." not in l]
                            if target_links:
                                return max(target_links, key=len)
            except:
                pass
            time.sleep(poll_interval)
        return None

class Hotmail007API:
    BASE_URL = "https://api.hotmail007.com"
    def __init__(self, client_key: str = ""):
        self.client_key = client_key
        self._email_data = None
    def create_account(self, email: str = None, password: str = None, proxy: str = None):
        if not self.client_key:
            return None
        for mail_type in ["outlook", "hotmail"]:
            try:
                r = requests.get(f"{self.BASE_URL}/api/mail/getMail",
                    params={"clientKey": self.client_key, "mailType": mail_type, "quantity": 1}, timeout=15, verify=False)
                if r.status_code == 200:
                    data = r.json()
                    if data.get("success") and data.get("code") == 0 and data.get("data"):
                        parts = data["data"][0].split(":")
                        if len(parts) >= 2:
                            self._email_data = {"email": parts[0], "password": parts[1]}
                            return parts[0]
            except:
                pass
        return None
    def get_verify_url(self, email: str, poll_interval: int = 5, timeout: int = 120, proxy: str = None):
        return None

class ZeusProvider:
    BASE_URL = "https://api.zeus-x.ru"
    def __init__(self, api_key: str = "", mail_type: str = "new", mailcode: str = ""):
        self.api_key = api_key
        if mailcode:
            self.account_codes = [mailcode]
        else:
            self.account_codes = ["HOTMAIL_TRUSTED_GRAPH_API", "OUTLOOK_TRUSTED_GRAPH_API"] if mail_type == "uhq" else ["HOTMAIL", "OUTLOOK"]
        self._email_data = None
        self._last_error = None

    def check_balance(self):
        try:
            r = requests.get(f"{self.BASE_URL}/balance", params={"apikey": self.api_key}, timeout=10)
            if r.status_code == 200:
                data = r.json()
                # Try multiple possible response formats
                if isinstance(data, dict):
                    for key in ["Balance", "balance", "data", "Data"]:
                        val = data.get(key)
                        if val is not None:
                            if isinstance(val, dict):
                                for k2 in ["Balance", "balance", "Amount", "amount"]:
                                    v2 = val.get(k2)
                                    if v2 is not None:
                                        return v2
                            else:
                                return val
                return data  # Return raw response if nothing matched
        except:
            pass
        return None

    def check_stock(self):
        try:
            r = requests.get(f"{self.BASE_URL}/instock", timeout=10)
            if r.status_code == 200:
                return r.json()
        except:
            pass
        return None
        
    def create_account(self, email: str = None, password: str = None, proxy: str = None):
        if not self.api_key:
            self._last_error = "no_api_key"
            return None
        self._last_error = None
        for code in self.account_codes:
            try:
                r = requests.get(f"{self.BASE_URL}/purchase",
                    params={"apikey": self.api_key, "accountcode": code, "quantity": 1}, timeout=10)
                if r.status_code == 200:
                    data = r.json()
                    if data.get("Code") == 0 and data.get("Data"):
                        accounts = data["Data"].get("Accounts", [])
                        if accounts:
                            item = accounts[0]
                            self._email_data = {
                                "email": item.get("Email", ""), 
                                "password": item.get("Password", ""),
                                "token": item.get("RefreshToken", ""),
                                "uuid": item.get("ClientId", "")
                            }
                            return item.get("Email", "")
                    # Store the error reason
                    msg = data.get("Message", data.get("message", ""))
                    err_code = data.get("Code", "")
                    self._last_error = msg or f"code={err_code}"
            except:
                self._last_error = "request_failed"
        return None
        
    def get_access_token(self, refresh_token: str, client_id: str = None) -> str:
        try:
            cid = client_id or "d8fbe69d-15be-43fa-b204-5c5bc5a73ad7"
            if refresh_token.endswith("$"): 
                refresh_token = refresh_token[:-1]
            response = requests.post(
                "https://login.microsoftonline.com/common/oauth2/v2.0/token",
                data={
                    "client_id": cid,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token",
                    "scope": "https://graph.microsoft.com/.default",
                },
                timeout=30, verify=False,
            )
            return response.json().get("access_token")
        except:
            return None

    def get_verify_url(self, email_str: str, poll_interval: int = 5, timeout: int = 120, proxy: str = None):
        if not self._email_data:
            return None
            
        refresh_token = self._email_data.get("token", "")
        client_id = self._email_data.get("uuid", "")
        
        if refresh_token:
            access_token = self.get_access_token(refresh_token, client_id)
            if access_token:
                session = requests.Session()
                start_time = time.time()
                while time.time() - start_time < timeout:
                    for folder in ["inbox", "junkemail"]:
                        try:
                            response = session.get(
                                f"https://graph.microsoft.com/v1.0/me/mailFolders/{folder}/messages",
                                headers={"Authorization": f"Bearer {access_token}"},
                                params={"$top": 10, "$orderby": "receivedDateTime desc", "$select": "subject,body,from"},
                                timeout=15, verify=False,
                            )
                            if response.status_code == 200:
                                emails = response.json().get("value", [])
                                for eml in emails:
                                    subject = eml.get("subject", "").lower()
                                    from_addr = eml.get("from", {}).get("emailAddress", {}).get("address", "").lower()
                                    is_verify = ("verify" in subject or "confirm" in subject or "email" in subject) and ("discord" in from_addr or "noreply@discord.com" in from_addr)
                                    if is_verify:
                                        body_html = eml.get("body", {}).get("content", "")
                                        direct_match = re.search(r'https://discord\.com/verify\?token=[^"\'\>\s]+', body_html)
                                        if direct_match:
                                            return direct_match.group(0).replace("&amp;", "&")
                                        for pat in [r'https://click\.discord\.com/ls/click\?[^"\'\>\s]+', r'https://links\.discord\.com[^"\'\>\s]+']:
                                            for m in re.finditer(pat, body_html):
                                                url = m.group(0).replace("&amp;", "&")
                                                try:
                                                    r2 = session.get(url, allow_redirects=True, verify=False, timeout=10)
                                                    if "discord.com/verify" in r2.url:
                                                        return r2.url
                                                    found = re.search(r'https://discord\.com/verify\?token=[^"\'\>\s]+', r2.text)
                                                    if found:
                                                        return found.group(0).replace("&amp;", "&")
                                                except:
                                                    pass
                        except Exception:
                            pass
                    time.sleep(poll_interval)
                return None
                
        # Fallback to standard IMAP if no refresh token
        password = self._email_data.get("password")
        if not password:
            return None
        start_time = time.time()
        while time.time() - start_time < timeout / 2: # Give it limited time for fallback
            try:
                mail = imaplib.IMAP4_SSL('outlook.office365.com')
                mail.login(email_str, password)
                for folder in ['inbox', 'Junk', '"Junk Email"']:
                    try:
                        status, count = mail.select(folder)
                        if status != 'OK': continue
                        status, messages = mail.search(None, '(ALL)')
                        if status == 'OK' and messages[0]:
                            for num in reversed(messages[0].split()):
                                res, msg_data = mail.fetch(num, '(RFC822)')
                                if res == 'OK':
                                    msg = email.message_from_bytes(msg_data[0][1])
                                    subject = str(msg.get("Subject", "")).lower()
                                    from_addr = str(msg.get("From", "")).lower()
                                    if "discord" in subject or "verify" in subject or "discord" in from_addr:
                                        body = ""
                                        if msg.is_multipart():
                                            for part in msg.walk():
                                                if part.get_content_type() in ["text/plain", "text/html"]:
                                                    try: body += part.get_payload(decode=True).decode(errors='ignore')
                                                    except: pass
                                        else:
                                            try: body = msg.get_payload(decode=True).decode(errors='ignore')
                                            except: pass
                                        if body:
                                            for pat in [r'https://discord\.com/verify/[^\s"\'<>]+', r'https://discord\.com/verify\?token=[^\s"\'<>]+', r'https://click\.discord\.com/[^\s"\'<>]+']:
                                                m = re.search(pat, body, re.IGNORECASE)
                                                if m: return m.group(0).replace("&amp;", "&")
                    except Exception:
                        pass
            except Exception as e:
                print(f"[IMAP LOGIN FAILED] {e}", flush=True)
            time.sleep(poll_interval)
        return None

class DraxonoAPI:
    BASE_URL = "https://mail.draxono.in/api"
    def __init__(self, api_key: str = ""):
        self.api_key = api_key
        self.headers = {"x-api-key": api_key} if api_key else {}
    def create_account(self, email: str = None, password: str = None, proxy: str = None):
        try:
            r = requests.get(f"{self.BASE_URL}/domains", headers=self.headers, timeout=10, verify=False)
            if r.status_code == 200:
                domains = r.json()
                if isinstance(domains, list) and domains:
                    domain = random.choice(domains)
                    local = ''.join(random.choices(string.ascii_lowercase + string.digits, k=12))
                    return f"{local}@{domain}"
        except:
            pass
        return None
    def get_verify_url(self, email: str, poll_interval: int = 5, timeout: int = 120, proxy: str = None):
        return None

class MailcowProvider:
    def __init__(self, mc_config: dict):
        self.config = mc_config
        self.base_url = mc_config.get("host", "")
        self.api_key = mc_config.get("api_key", "")
        self.headers = {"X-API-Key": self.api_key}
        self.tm_api = TempMailLolAPI()
        self.temp_email = None

    def create_account(self, email: str = None, password: str = None, proxy: str = None):
        if not self.base_url or not self.api_key:
            return None
        
        # 1. Generate tempmail target
        self.temp_email = self.tm_api.create_account()
        if not self.temp_email:
            return None
            
        try:
            # 2. Create Mailcow Alias forwarding to tempmail
            domain = self.config.get("domain", "")
            if not domain:
                return None
            alias = f"{''.join(random.choices(string.ascii_lowercase + string.digits, k=8))}@{domain}"
            data = {"address": alias, "goto": self.temp_email, "active": "1"}
            
            # format base url just in case user forgot https://
            url = self.base_url
            if not url.startswith('http'):
                url = f"https://{url}"
            if url.endswith('/'):
                url = url[:-1]
                
            r = requests.post(f"{url}/api/v1/add/alias", json=data, headers=self.headers, timeout=10)
            if r.status_code == 200:
                return alias
        except:
            pass
        return None

    def get_verify_url(self, email: str, poll_interval: int = 5, timeout: int = 120, proxy: str = None):
        if not self.temp_email:
            return None
        # Simply poll the mail.tm inbox we just created!
        return self.tm_api.get_verify_url(self.temp_email, poll_interval, timeout, proxy)

class LutionAPI(ZeusProvider):
    BASE_URL = "https://api.lution.ee/v2"
    def __init__(self, api_key: str = "", category: str = "Microsoft"):
        self.api_key = api_key
        self.category = category
        self._email_data = None
        
    def create_account(self, email: str = None, password: str = None, proxy: str = None):
        if not self.api_key:
            return None
        headers = {"accept": "application/json", "Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"}
        payload = {"category": self.category, "quantity": 1}
        for _ in range(5):
            try:
                r = requests.post(f"{self.BASE_URL}/email/buy", json=payload, headers=headers, timeout=10)
                if r.status_code == 200:
                    j = r.json()
                    data = j.get("data") or {}
                    emails = data.get("emails") or []
                    if emails:
                        e = emails[0]
                        self._email_data = {
                            "email": e.get("email", ""), 
                            "password": e.get("password", ""),
                            "token": e.get("graph_refresh_token", ""),
                            "uuid": e.get("thunderbird_client_id", "")
                        }
                        return e.get("email", "").lower()
            except:
                pass
            time.sleep(3)
        return None

def get_mail_provider():
    services = config.get("mail_services", {})
    if not services:
        devs_cfg = config.get("devs_mail", {})
        if devs_cfg.get("api_key"):
            return APZMailApi(logger=print, api_key=devs_cfg["api_key"]), "cybertemp"
        return None, None

    provider_order = ["duckmail", "cybertemp", "lution", "tempmail_lol", "hotmail007", "zeus", "draxono", "mailcow"]
    for name in provider_order:
        svc = services.get(name, {})
        if not svc.get("enabled", False):
            continue
        if name == "duckmail":
            return DuckMailAPI(password=svc.get("password", "")), name
        elif name == "cybertemp":
            return APZMailApi(logger=print, api_key=svc.get("api_key", "")), name
        elif name == "lution":
            return LutionAPI(api_key=svc.get("api_key", ""), category=svc.get("mailcode", "")), name
        elif name == "tempmail_lol":
            return TempMailLolAPI(), name
        elif name == "hotmail007":
            return Hotmail007API(client_key=svc.get("client_key", "")), name
        elif name == "zeus":
            return ZeusProvider(api_key=svc.get("api_key", ""), mailcode=svc.get("mailcode", "")), name
        elif name == "draxono":
            return DraxonoAPI(api_key=svc.get("api_key", "")), name
        elif name == "mailcow":
            return MailcowProvider(svc), name
    return None, None

class Solver:
    VPS_URL  = "https://9captcha-api.pridesmp.fun"                
    UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36'
    
    def __init__(self, url, sitekey, rqdata="", user_agent="", proxy=None, api_key="",
                 session_profile=None, discord_fingerprint=None, cookies=None,
                 super_props=None, captcha_rqtoken=None, captcha_session_id=None):
        self.url        = url
        self.sitekey    = sitekey
        self.rqdata     = rqdata
        self.user_agent = user_agent
        self.proxy      = proxy
        self.api_key    = api_key
        self.session_profile      = session_profile
        self.discord_fingerprint  = discord_fingerprint
        self.cookies              = cookies if isinstance(cookies, dict) else {}
        self.super_props           = super_props
        self.captcha_rqtoken       = captcha_rqtoken
        self.captcha_session_id    = captcha_session_id
        cap_cfg = config.get("9captcha", {})
        self.use_extension = cap_cfg.get("extension_solver", True)
        self.use_vps       = cap_cfg.get("req_solver", False)

    def _format_proxy(self):
        if self.proxy:
            return self.proxy
        return ""
    def _solve_extension(self, timeout=90):
        
        try:
            from engine.extension_browser import get_browser
            browser = get_browser()
            _file_log("[EXT] Solving via local browser + extension")
            token = browser.solve(
                sitekey=self.sitekey,
                url=self.url,
                rqdata=self.rqdata,
                user_agent=self.user_agent,
                timeout=timeout,
                proxy=self.proxy,
            )
            if token:
                return token, {}
            _file_log("[EXT] Extension solver returned no token")
            return None, None
        except ImportError:
            _file_log("[EXT] extension_browser.py not found or truedriver not installed")
            return None, None
        except Exception as e:
            _file_log(f"[EXT] Error: {e}")
            return None, None
    def _solve_vps(self, timeout=120, poll_interval=2):
        import urllib.request, urllib.error, json, time

        # Forward captcha_rqtoken and captcha_session_id if Discord provided them
        extra_data = {}
        if self.captcha_rqtoken:
            extra_data["captcha_rqtoken"] = self.captcha_rqtoken
        if self.captcha_session_id:
            extra_data["captcha_session_id"] = self.captcha_session_id

        payload = {
            "key": self.api_key,
            "type": "hcaptcha_basic",
            "data": {
                "sitekey": self.sitekey,
                "siteurl": self.url.replace("https://", "").replace("http://", "").split("/")[0],
                "proxy": self._format_proxy(),
                "rqdata": self.rqdata,
                "useragent": self.user_agent,
                **extra_data
            }
        }
        
        _file_log(f"[VPS] Creating task on {self.VPS_URL}...")
        
        req = urllib.request.Request(
            f"{self.VPS_URL}/api/create_task",
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json', 'User-Agent': self.UA}
        )
        try:
            resp = urllib.request.urlopen(req, timeout=15)
            resp_text = resp.read().decode('utf-8')
            data = json.loads(resp_text)
            if data.get("status") != "success":
                _file_log(f"[VPS] Task creation failed: {data.get('message')}")
                return None, None
            task_id = data.get("task_id")
        except Exception as e:
            _file_log(f"[VPS] API connection error: {e}")
            return None, None
            
        _file_log(f"[VPS] Task {task_id} created, polling...")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            time.sleep(poll_interval)
            try:
                poll_url = f"{self.VPS_URL}/api/get_result/{task_id}?key={self.api_key}"
                poll_req = urllib.request.Request(poll_url, headers={'User-Agent': self.UA})
                poll_resp = urllib.request.urlopen(poll_req, timeout=15)
                poll_data = json.loads(poll_resp.read().decode('utf-8'))
                
                status = poll_data.get("status")
                if status == "solved":
                    _file_log(f"[VPS] Solved successfully in {round(time.time() - start_time, 1)}s")
                    return poll_data.get("solution"), {}
                elif status == "error":
                    err_msg = poll_data.get("error", "Unknown error")
                    _file_log(f"[VPS] Solver API returned error: {err_msg}")
                    if "rate limit" in str(err_msg).lower() or "429" in str(err_msg):
                        return "ERROR_RATELIMIT", None
                    if "ip" in str(err_msg).lower() or "proxy" in str(err_msg).lower() or "reject" in str(err_msg).lower():
                        return "ERROR_IP_REJECTED", None
                    return None, None
                elif status == "solving":
                    continue
            except Exception as e:
                _file_log(f"[VPS] Polling error: {e}")
        
        _file_log("[VPS] Task timed out")
        return None, None

    def solve(self, timeout=120, poll_interval=2):
        _file_log(f"Using Proxy: {self.proxy or 'None (Local IP)'}")
        _file_log(f"Solver config: ext={self.use_extension}, vps={self.use_vps}")
        
        if self.use_extension:
            _file_log("[EXT] Using extension solver ")
            try:
                result = self._solve_extension(timeout)
                if result[0]:
                    return result
                _file_log("[EXT] Failed")
            except Exception as e:
                _file_log(f"[EXT] Error: {e}")
            return None, None
        if self.use_vps:
            _file_log("[REQ] Using Req solver (request mode)")
            try:
                return self._solve_vps(timeout, poll_interval)
            except Exception as e:
                _file_log(f"[VPS] Error: {e}")
                return None, None
        _file_log("[WARN] No solver enabled! Set extension_solver or req_solver in config.")
        return None, None
config = {}
try:
    with open(os.path.join(os.path.dirname(__file__), "config.json"), "r") as f:
        config = json.load(f)
except Exception as e:
    print(f"Error loading config.json: {e}")

_logs_enabled = config.get("logs", False)
_debug_enabled = True  # Always log registration debug
def _file_log(msg):
    if not _logs_enabled:
        return
    try:
        with open(os.path.join(os.path.dirname(__file__), "logs.txt"), "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}\n")
    except Exception:
        pass
def _debug_log(msg):
    """Always write debug logs to debug_register.txt for troubleshooting."""
    try:
        with open(os.path.join(os.path.dirname(__file__), "debug_register.txt"), "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}\n")
    except Exception:
        pass
def _clear_debug_log():
    """Clear the debug register log at start of each run."""
    try:
        p = os.path.join(os.path.dirname(__file__), "debug_register.txt")
        if os.path.exists(p):
            os.remove(p)
    except Exception:
        pass

verification_enabled = config.get("verification", {}).get("enabled", True)
gen_count = 0
gen_lock = threading.Lock()
stats_lock = threading.Lock()
stats = {
    'generated': 0,
    'verified': 0,
    'captcha_failed': 0,
    'captcha_solved': 0,
    'locked': 0,
    'valid': 0,
    'total': 0
}
class ProxyManager:
    
    COOLDOWN_SECONDS = 30  # Minimum seconds between reuse of the same proxy
    MAX_FAILURES = 3       # Mark proxy dead after this many consecutive failures
    
    def __init__(self, file_path="input/proxies.txt", resi_path="input/resi.txt"):
        self.file_path = file_path
        self.resi_path = resi_path
        self.lock = threading.Lock()
        self._pool = []           # All available proxies
        self._in_use = set()      # Currently checked-out proxies
        self._last_used = {}      # proxy -> timestamp of last use
        self._fail_count = {}     # proxy -> consecutive failure count
        self._dead = set()        # Permanently failed proxies
        self._index = 0           # Round-robin pointer
        self._loaded = False
    
    def _load_pool(self):
        if self._loaded:
            return
        for path in [self.file_path, self.resi_path]:
            if not os.path.exists(path):
                continue
            try:
                with open(path, "r", encoding="utf-8") as f:
                    for line in f:
                        raw = line.strip()
                        if raw and raw not in self._pool:
                            proxy = self._normalize_proxy(raw)
                            if proxy and proxy not in self._pool:
                                self._pool.append(proxy)
            except Exception:
                pass
        self._loaded = True
    
    def _normalize_proxy(self, proxy):
        user_pass = ""
        host_port = ""
        if "@" in proxy:
            user_pass, host_port = proxy.split("@", 1)
        else:
            host_port = proxy
        if "dataimpulse" in host_port.lower() and user_pass:
            if ":" in user_pass:
                user, pwd = user_pass.split(":", 1)
                if "__session" not in user:
                    sess_id = uuid.uuid4().hex[:8]
                    user_pass = f"{user}__session_{sess_id}:{pwd}"
        import socket
        if ":" in host_port:
            host, port = host_port.rsplit(":", 1)
            try:
                resolved_ip = socket.gethostbyname(host)
                host_port = f"{resolved_ip}:{port}"
            except Exception:
                pass
        if user_pass:
            return f"{user_pass}@{host_port}"
        return host_port
    
    def get_proxy(self):
        with self.lock:
            self._load_pool()
            if not self._pool:
                return None
            now = time.time()
            pool_size = len(self._pool)
            # Try each proxy in round-robin order
            for _ in range(pool_size):
                proxy = self._pool[self._index % pool_size]
                self._index = (self._index + 1) % pool_size
                # Skip dead proxies
                if proxy in self._dead:
                    continue
                # Skip proxies currently checked out
                if proxy in self._in_use:
                    continue
                # Enforce cooldown — don't reuse the same IP too quickly
                last = self._last_used.get(proxy, 0)
                if now - last < self.COOLDOWN_SECONDS:
                    continue
                # Found a good proxy
                self._in_use.add(proxy)
                self._last_used[proxy] = now
                return proxy
            # Fallback: all proxies on cooldown or in-use, return least-recently-used
            available = [p for p in self._pool if p not in self._dead and p not in self._in_use]
            if available:
                best = min(available, key=lambda p: self._last_used.get(p, 0))
                self._in_use.add(best)
                self._last_used[best] = now
                return best
            # Last resort: all proxies in-use, just pick any alive one
            alive = [p for p in self._pool if p not in self._dead]
            if alive:
                pick = alive[self._index % len(alive)]
                self._last_used[pick] = now
                return pick
            return None
    
    def release_proxy(self, proxy):
        with self.lock:
            self._in_use.discard(proxy)
    
    def mark_bad(self, proxy):
        with self.lock:
            self._fail_count[proxy] = self._fail_count.get(proxy, 0) + 1
            if self._fail_count[proxy] >= self.MAX_FAILURES:
                self._dead.add(proxy)
                self._in_use.discard(proxy)
    
    def mark_good(self, proxy):
        with self.lock:
            self._fail_count[proxy] = 0
    
    def pop_top(self):
        return self.get_proxy()
    
    def pop_resi(self):
        return self.get_proxy()

proxy_manager = ProxyManager()
from colorama import Fore, Style, init
from pystyle import Colors, Colorate, Center, Anime, System
init(autoreset=True)
class Log:
    lock = threading.Lock()
    @staticmethod
    def _log(icon, text, color=R):
        with Log.lock:
            print(f"  {D}│{R} {icon} {color}{text}{R}")
    @staticmethod
    def proxy_header(num, proxy):
        if not proxy:
            return
        censor = config.get("censor", True)
        if censor:
            if '@' in proxy:
                auth, hostport = proxy.rsplit('@', 1)
                if ':' in auth:
                    user, pwd = auth.split(':', 1)
                    censored_user = user[:6] + '***'
                    censored_pwd = '****'
                    censored_proxy = f"{censored_user}:{censored_pwd}@{hostport}"
                else:
                    censored_proxy = auth[:6] + '***@' + hostport
            else:
                censored_proxy = proxy[:10] + '***'
            Log._log(f"{P}⟐{R}", f"{censored_proxy}", D)
        else:
            Log._log(f"{P}⟐{R}", f"{proxy}", D)
    @staticmethod
    def generated(token):
        with Log.lock:
            parts = token.split(".")
            if len(parts) == 3:
                censored_token = f"{parts[0][:6]}******.{parts[1]}.*******{parts[2][-6:]}"
            else:
                censored_token = token[:15] + "******"
            print(f"  {D}│{R} {G}✓{R} {G}Generated{R} {C}{censored_token}{R}")
        with stats_lock:
            stats['generated'] += 1
            stats['total'] += 1
    @staticmethod
    def captcha_solved(time_n, token=""):
        token_str = f" → {token[:40]}..." if token else ""
        Log._log(f"{C}⚡{R}", f"Captcha solved in {time_n:.1f}s{token_str}", C)
        with stats_lock:
            stats['captcha_solved'] += 1
    @staticmethod
    def solving(email):
        Log._log(f"{Y}⏳{R}", "Solving captcha...", Y)
    @staticmethod
    def captcha_failed():
        Log._log(f"{Fore.RED}✗{R}", "Captcha failed due to captcha ratelimit / timeout", Fore.RED)
        with stats_lock:
            stats['captcha_failed'] += 1
            stats['total'] += 1
    @staticmethod
    def status(status_text):
        Log._log(f"{P}›{R}", status_text, Fore.MAGENTA)
    @staticmethod
    def error(text):
        Log._log(f"{Fore.RED}✗{R}", text, Fore.RED)
    @staticmethod
    def waiting(text):
        Log._log(f"{Y}⏳{R}", text, Y)
    @staticmethod
    def verified(token):
        with Log.lock:
            parts = token.split(".")
            if len(parts) == 3:
                censored_token = f"{parts[0][:6]}******.{parts[1]}.*******{parts[2][-6:]}"
            else:
                censored_token = token[:15] + "******"
            print(f"  {D}│{R} {G}✓{R} {G}Verified{R}  {C}{censored_token}{R}")
        with stats_lock:
            stats['verified'] += 1
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.6897.75 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.7049.96 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.6998.127 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.6943.142 Safari/537.36",
]

# ── Browser Fingerprint Profiles ─────────────────────────────────────────────
# Each profile matches a real machine: UA + GPU + screen + memory + timezone.
# Discord correlates x-super-properties with WebGL/GPU data — mismatches trigger flags.
BROWSER_PROFILES = {
    "Windows Chrome 148 1080p NVIDIA": {
        "name": "Windows Chrome 148 1080p NVIDIA",
        "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
        "brands": [
            {"brand": "Google Chrome", "version": "148"},
            {"brand": "Chromium", "version": "148"},
            {"brand": "Not:A-Brand", "version": "99"},
        ],
        "platform": "Windows", "mobile": False, "os_version": "10",
        "gpu_vendor": "Google Inc. (NVIDIA)",
        "gpu_renderer": "ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0)",
        "screen_w": 1920, "screen_h": 1080,
        "lang": "en-US", "langs": ["en-US", "en"],
        "timezone": "America/New_York", "tz_offset": -300,
        "cores": 12, "memory": 8,
    },
    "Windows Chrome 148 1440p AMD": {
        "name": "Windows Chrome 148 1440p AMD",
        "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
        "brands": [
            {"brand": "Chromium", "version": "148"},
            {"brand": "Not:A-Brand", "version": "99"},
            {"brand": "Google Chrome", "version": "148"},
        ],
        "platform": "Windows", "mobile": False, "os_version": "10",
        "gpu_vendor": "Google Inc. (AMD)",
        "gpu_renderer": "ANGLE (AMD, AMD Radeon RX 6700 XT Direct3D11 vs_5_0 ps_5_0)",
        "screen_w": 2560, "screen_h": 1440,
        "lang": "en-US", "langs": ["en-US", "en"],
        "timezone": "America/Chicago", "tz_offset": -360,
        "cores": 16, "memory": 16,
    },
    "Windows Chrome 148 1080p Intel": {
        "name": "Windows Chrome 148 1080p Intel",
        "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
        "brands": [
            {"brand": "Chromium", "version": "148"},
            {"brand": "Google Chrome", "version": "148"},
            {"brand": "Not:A-Brand", "version": "99"},
        ],
        "platform": "Windows", "mobile": False, "os_version": "10",
        "gpu_vendor": "Google Inc. (Intel)",
        "gpu_renderer": "ANGLE (Intel, Intel(R) UHD Graphics 770 Direct3D11 vs_5_0 ps_5_0)",
        "screen_w": 1920, "screen_h": 1080,
        "lang": "en-US", "langs": ["en-US", "en"],
        "timezone": "America/Denver", "tz_offset": -420,
        "cores": 8, "memory": 16,
    },
    "Windows Chrome 147 1366x768 Laptop": {
        "name": "Windows Chrome 147 1366x768 Laptop",
        "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36",
        "brands": [
            {"brand": "Google Chrome", "version": "147"},
            {"brand": "Chromium", "version": "147"},
            {"brand": "Not:A-Brand", "version": "99"},
        ],
        "platform": "Windows", "mobile": False, "os_version": "10",
        "gpu_vendor": "Google Inc. (Intel)",
        "gpu_renderer": "ANGLE (Intel, Intel(R) UHD Graphics Direct3D11 vs_5_0 ps_5_0)",
        "screen_w": 1366, "screen_h": 768,
        "lang": "en-US", "langs": ["en-US", "en"],
        "timezone": "America/Los_Angeles", "tz_offset": -480,
        "cores": 4, "memory": 8,
    },
    "Windows Chrome 148 1080p RTX4060": {
        "name": "Windows Chrome 148 1080p RTX4060",
        "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
        "brands": [
            {"brand": "Google Chrome", "version": "148"},
            {"brand": "Not:A-Brand", "version": "99"},
            {"brand": "Chromium", "version": "148"},
        ],
        "platform": "Windows", "mobile": False, "os_version": "10",
        "gpu_vendor": "Google Inc. (NVIDIA)",
        "gpu_renderer": "ANGLE (NVIDIA, NVIDIA GeForce RTX 4060 Direct3D11 vs_5_0 ps_5_0)",
        "screen_w": 1920, "screen_h": 1080,
        "lang": "en-US", "langs": ["en-US", "en"],
        "timezone": "America/Los_Angeles", "tz_offset": -480,
        "cores": 8, "memory": 16,
    },
    "Windows 11 Chrome 148 4K": {
        "name": "Windows 11 Chrome 148 4K",
        "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
        "brands": [
            {"brand": "Google Chrome", "version": "148"},
            {"brand": "Chromium", "version": "148"},
            {"brand": "Not:A-Brand", "version": "99"},
        ],
        "platform": "Windows", "mobile": False, "os_version": "11",
        "gpu_vendor": "Google Inc. (NVIDIA)",
        "gpu_renderer": "ANGLE (NVIDIA, NVIDIA GeForce RTX 4070 Direct3D11 vs_5_0 ps_5_0)",
        "screen_w": 3840, "screen_h": 2160,
        "lang": "en-US", "langs": ["en-US", "en"],
        "timezone": "America/New_York", "tz_offset": -300,
        "cores": 24, "memory": 16,
    },
    "macOS Chrome 148 Retina": {
        "name": "macOS Chrome 148 Retina",
        "userAgent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
        "brands": [
            {"brand": "Google Chrome", "version": "148"},
            {"brand": "Chromium", "version": "148"},
            {"brand": "Not:A-Brand", "version": "99"},
        ],
        "platform": "macOS", "mobile": False, "os_version": "10.15.7",
        "gpu_vendor": "Google Inc. (Apple)",
        "gpu_renderer": "ANGLE (Apple, ANGLE Metal Renderer: Apple M2, Unspecified Version)",
        "screen_w": 1728, "screen_h": 1117,
        "lang": "en-US", "langs": ["en-US", "en"],
        "timezone": "America/Los_Angeles", "tz_offset": -480,
        "cores": 8, "memory": 8,
    },
    "macOS Chrome 147 MBA": {
        "name": "macOS Chrome 147 MBA",
        "userAgent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36",
        "brands": [
            {"brand": "Chromium", "version": "147"},
            {"brand": "Google Chrome", "version": "147"},
            {"brand": "Not:A-Brand", "version": "99"},
        ],
        "platform": "macOS", "mobile": False, "os_version": "10.15.7",
        "gpu_vendor": "Google Inc. (Apple)",
        "gpu_renderer": "ANGLE (Apple, ANGLE Metal Renderer: Apple M1, Unspecified Version)",
        "screen_w": 1440, "screen_h": 900,
        "lang": "en-US", "langs": ["en-US", "en"],
        "timezone": "America/Chicago", "tz_offset": -360,
        "cores": 8, "memory": 8,
    },
    "Linux Chrome 148 1080p": {
        "name": "Linux Chrome 148 1080p",
        "userAgent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
        "brands": [
            {"brand": "Google Chrome", "version": "148"},
            {"brand": "Chromium", "version": "148"},
            {"brand": "Not:A-Brand", "version": "99"},
        ],
        "platform": "Linux", "mobile": False, "os_version": "",
        "gpu_vendor": "Mesa", "gpu_renderer": "Mesa Intel(R) UHD Graphics 630 (CFL GT2)",
        "screen_w": 1920, "screen_h": 1080,
        "lang": "en-US", "langs": ["en-US", "en"],
        "timezone": "Europe/London", "tz_offset": 0,
        "cores": 8, "memory": 16,
    },
    "Windows Chrome 147 1080p RTX2070": {
        "name": "Windows Chrome 147 1080p RTX2070",
        "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36",
        "brands": [
            {"brand": "Chromium", "version": "147"},
            {"brand": "Not:A-Brand", "version": "99"},
            {"brand": "Google Chrome", "version": "147"},
        ],
        "platform": "Windows", "mobile": False, "os_version": "10",
        "gpu_vendor": "Google Inc. (NVIDIA)",
        "gpu_renderer": "ANGLE (NVIDIA, NVIDIA GeForce RTX 2070 SUPER Direct3D11 vs_5_0 ps_5_0)",
        "screen_w": 1920, "screen_h": 1080,
        "lang": "en-US", "langs": ["en-US", "en"],
        "timezone": "Europe/Berlin", "tz_offset": 60,
        "cores": 8, "memory": 16,
    },
    "Windows Chrome 148 Ultrawide": {
        "name": "Windows Chrome 148 Ultrawide",
        "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
        "brands": [
            {"brand": "Chromium", "version": "148"},
            {"brand": "Google Chrome", "version": "148"},
            {"brand": "Not:A-Brand", "version": "99"},
        ],
        "platform": "Windows", "mobile": False, "os_version": "11",
        "gpu_vendor": "Google Inc. (AMD)",
        "gpu_renderer": "ANGLE (AMD, AMD Radeon RX 7900 XT Direct3D11 vs_5_0 ps_5_0)",
        "screen_w": 3440, "screen_h": 1440,
        "lang": "en-US", "langs": ["en-US", "en"],
        "timezone": "America/New_York", "tz_offset": -300,
        "cores": 16, "memory": 32,
    },
    "macOS Chrome 148 iMac": {
        "name": "macOS Chrome 148 iMac",
        "userAgent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
        "brands": [
            {"brand": "Google Chrome", "version": "148"},
            {"brand": "Not:A-Brand", "version": "99"},
            {"brand": "Chromium", "version": "148"},
        ],
        "platform": "macOS", "mobile": False, "os_version": "10.15.7",
        "gpu_vendor": "Google Inc. (Apple)",
        "gpu_renderer": "ANGLE (Apple, ANGLE Metal Renderer: Apple M3, Unspecified Version)",
        "screen_w": 2560, "screen_h": 1440,
        "lang": "en-US", "langs": ["en-US", "en"],
        "timezone": "America/New_York", "tz_offset": -300,
        "cores": 12, "memory": 16,
    },
}

def resolve_session_profile(profile_name=None):
    """Pick a browser profile and build session-level metadata from it."""
    if profile_name and profile_name in BROWSER_PROFILES:
        prof = BROWSER_PROFILES[profile_name]
    else:
        prof = random.choice(list(BROWSER_PROFILES.values()))
    ua = prof["userAgent"]
    m = re.search(r"Chrome/(\d+)", ua)
    chrome_major = int(m.group(1)) if m else 148
    brands = prof.get("brands", [])
    sec_ch_ua = ", ".join(f'"{b["brand"]}";v="{b["version"]}"' for b in brands)
    plat = prof.get("platform", "Windows")
    os_version = prof.get("os_version", "10")
    if plat == "macOS":
        sp_os, sp_browser, sp_device = "Mac OS X", "Chrome", ""
    elif plat == "Linux":
        sp_os, sp_browser, sp_device = "Linux", "Chrome", ""
    else:
        sp_os, sp_browser, sp_device = "Windows", "Chrome", ""
    return {
        "ua": ua,
        "chrome_version": chrome_major,
        "sec_ch_ua": sec_ch_ua,
        "sec_ch_ua_mobile": "?0",
        "sec_ch_ua_platform": f'"{plat}"',
        "platform": plat,
        "os_version": os_version,
        "lang": prof.get("lang", "en-US"),
        "timezone": prof.get("timezone", "America/Los_Angeles"),
        "sp_os": sp_os,
        "sp_browser": sp_browser,
        "sp_device": sp_device,
        "raw_profile": prof,
        "name": prof.get("name", "Unknown"),
    }

# ── Custom fingerprint loading ───────────────────────────────────────────────
_CUSTOM_FINGERPRINTS = []
_FINGERPRINTS_LOADED = False
_FINGERPRINTS_LOCK = threading.Lock()

def load_custom_fingerprints():
    global _CUSTOM_FINGERPRINTS, _FINGERPRINTS_LOADED
    with _FINGERPRINTS_LOCK:
        if _FINGERPRINTS_LOADED:
            return
        _FINGERPRINTS_LOADED = True
        fp_path = os.path.join(os.path.dirname(__file__), "input", "fingerprints.txt")
        if not os.path.exists(fp_path):
            return
        with open(fp_path, "r", encoding="utf-8") as f:
            _CUSTOM_FINGERPRINTS.extend(line.strip() for line in f if line.strip())

def pop_custom_fingerprint():
    """Return a pre-harvested Discord fingerprint if available."""
    with _FINGERPRINTS_LOCK:
        if _CUSTOM_FINGERPRINTS:
            return _CUSTOM_FINGERPRINTS.pop(0)
    return None

_FIRST_NAMES = [
    'james', 'mary', 'john', 'patricia', 'robert', 'jennifer', 'michael', 'linda', 'william', 'elizabeth',
    'david', 'barbara', 'richard', 'susan', 'joseph', 'jessica', 'thomas', 'sarah', 'charles', 'karen',
    'christopher', 'lisa', 'daniel', 'nancy', 'matthew', 'betty', 'anthony', 'margaret', 'mark', 'sandra',
    'donald', 'ashley', 'steven', 'kimberly', 'paul', 'emily', 'andrew', 'donna', 'joshua', 'michelle',
    'kenneth', 'carol', 'kevin', 'amanda', 'brian', 'dorothy', 'george', 'melissa', 'timothy', 'deborah',
    'ronald', 'stephanie', 'edward', 'rebecca', 'jason', 'sharon', 'jeffrey', 'laura', 'ryan', 'cynthia',
    'jacob', 'kathleen', 'gary', 'amy', 'nicholas', 'angela', 'eric', 'shirley', 'jonathan', 'anna',
    'stephen', 'brenda', 'larry', 'pamela', 'justin', 'emma', 'scott', 'nicole', 'brandon', 'helen',
    'alex', 'sam', 'jay', 'riley', 'max', 'charlie', 'taylor', 'jordan', 'casey', 'drew', 'oliver', 'lucas',
    'mason', 'logan', 'ethan', 'aiden', 'jackson', 'liam', 'noah', 'elijah', 'mia', 'chloe', 'zoey', 'lily'
]

_LAST_NAMES = [
    'smith', 'johnson', 'williams', 'brown', 'jones', 'garcia', 'miller', 'davis', 'rodriguez', 'martinez',
    'hernandez', 'lopez', 'gonzalez', 'wilson', 'anderson', 'thomas', 'taylor', 'moore', 'jackson', 'martin',
    'lee', 'perez', 'thompson', 'white', 'harris', 'sanchez', 'clark', 'ramirez', 'lewis', 'robinson',
    'walker', 'young', 'allen', 'king', 'wright', 'scott', 'torres', 'nguyen', 'hill', 'flores', 'green',
    'adams', 'nelson', 'baker', 'hall', 'rivera', 'campbell', 'mitchell', 'carter', 'roberts', 'gomez',
    'phillips', 'evans', 'turner', 'diaz', 'parker', 'cruz', 'edwards', 'collins', 'reyes', 'stewart',
    'morris', 'morales', 'murphy', 'cook', 'rogers', 'gutierrez', 'ortiz', 'morgan', 'cooper', 'peterson',
    'bailey', 'reed', 'kelly', 'howard', 'ramos', 'kim', 'cox', 'ward', 'richardson', 'watson', 'brooks',
    'chavez', 'wood', 'james', 'bennett', 'gray', 'mendoza', 'ruiz', 'hughes', 'price', 'alvarez', 'castillo'
]

_ADJECTIVES = [
    'cool', 'dark', 'wild', 'fast', 'chill', 'epic', 'real', 'true', 'fire', 'ice',
    'neon', 'void', 'zen', 'pro', 'ace', 'rad', 'dope', 'lit', 'raw', 'hype', 'super',
    'mega', 'ultra', 'hyper', 'quantum', 'cyber', 'retro', 'crypto', 'meta', 'stealth',
    'shadow', 'ghost', 'phantom', 'ninja', 'vortex', 'solar', 'lunar', 'cosmic', 'astral',
    'mystic', 'magic', 'lucky', 'happy', 'mad', 'crazy', 'lazy', 'sleepy', 'angry', 'sad',
    'good', 'bad', 'evil', 'holy', 'pure', 'dirty', 'clean', 'fresh', 'stale', 'sweet'
]

def _random_username() -> str:
    patterns = [
        lambda: random.choice(_FIRST_NAMES) + random.choice(_LAST_NAMES) + str(random.randint(10, 9999)),
        lambda: random.choice(_FIRST_NAMES) + '_' + random.choice(_LAST_NAMES) + str(random.randint(10, 99)),
        lambda: random.choice(_ADJECTIVES) + random.choice(_FIRST_NAMES) + str(random.randint(100, 999)),
        lambda: random.choice(_FIRST_NAMES) + '.' + random.choice(_LAST_NAMES) + str(random.randint(1, 99)),
        lambda: random.choice(_FIRST_NAMES) + str(random.randint(1980, 2010)),
        lambda: random.choice(_LAST_NAMES) + random.choice(_FIRST_NAMES) + str(random.randint(10, 99)),
        lambda: random.choice(_ADJECTIVES) + '_' + random.choice(_FIRST_NAMES) + str(random.randint(10, 99)),
    ]
    return random.choice(patterns)()
def _random_password() -> str:
    
    base = ''.join(random.choices(string.ascii_letters, k=random.randint(6, 10)))
    digits = ''.join(random.choices(string.digits, k=random.randint(2, 4)))
    special = random.choice('!@#$%&*')
    pwd = base + digits + special
    return pwd
def _random_dob() -> str:
    
    year = random.randint(1994, 2006)
    month = random.randint(1, 12)
    day = random.randint(1, 28)  
    return f"{year}-{month:02d}-{day:02d}"
# ── Build number caching (6-hour TTL) ────────────────────────────────────────
_BUILD_CACHE = {"value": None, "ts": 0.0}
_BUILD_LOCK = threading.Lock()
_BUILD_TTL = 6 * 3600
_BUILD_FALLBACK = 502645

def get_build_number(proxy=None):
    now = time.time()
    with _BUILD_LOCK:
        if _BUILD_CACHE["value"] and now - _BUILD_CACHE["ts"] < _BUILD_TTL:
            return _BUILD_CACHE["value"]
    try:
        sess = StealthSession()
        if proxy:
            px = parse_proxy(proxy)
            if px: sess.proxies = {"http": px, "https": px}
        page = sess.get("https://discord.com/app", timeout=15).text
        assets = re.findall(r'src="/assets/([^"]+)"', page)
        for asset in reversed(assets):
            try:
                js = sess.get(f"https://discord.com/assets/{asset}", timeout=15).text
            except Exception:
                continue
            if "buildNumber:" in js:
                bn = int(js.split('buildNumber:"')[1].split('"')[0])
                with _BUILD_LOCK:
                    _BUILD_CACHE["value"] = bn
                    _BUILD_CACHE["ts"] = now
                return bn
    except Exception:
        pass
    return _BUILD_FALLBACK
def build_super_properties(build_number, session_profile):
    """Build x-super-properties using the full session profile."""
    ua = session_profile["ua"]
    chrome_match = re.search(r"Chrome/([\d.]+)", ua)
    browser_version = chrome_match.group(1) if chrome_match else f"{session_profile['chrome_version']}.0.0.0"
    payload = {
        "os": session_profile["sp_os"],
        "browser": session_profile["sp_browser"],
        "device": session_profile["sp_device"],
        "system_locale": session_profile["lang"],
        "browser_user_agent": ua,
        "browser_version": browser_version,
        "os_version": session_profile.get("os_version", ""),
        "referrer": "https://discord.com/",
        "referring_domain": "discord.com",
        "referrer_current": "",
        "referring_domain_current": "",
        "release_channel": "stable",
        "client_build_number": build_number,
        "client_event_source": None,
        "design_id": 0,
        "has_client_mods": False,
        "client_launch_id": str(uuid.uuid4()),
        "launch_signature": str(uuid.uuid4()),
        "client_heartbeat_session_id": str(uuid.uuid4()),
        "client_app_state": "focused",
    }
    raw = json.dumps(payload, separators=(",", ":")).encode()
    return base64.b64encode(raw).decode()
def _build_sec_ch_ua(chrome_version):
    if chrome_version >= 133:
        return f'"Not:A-Brand";v="24", "Chromium";v="{chrome_version}", "Google Chrome";v="{chrome_version}"'
    return f'"Not_A Brand";v="8", "Chromium";v="{chrome_version}", "Google Chrome";v="{chrome_version}"'
def acquire_discord_cookies(session):
    session.get("https://discord.com")
    cookies = session.cookies.get_dict()
    dcfduid = cookies.get("__dcfduid")
    sdcfduid = cookies.get("__sdcfduid")
    return dcfduid, sdcfduid
def fetch_discord_fingerprint(session, dcfduid, sdcfduid, session_profile):
    """Fetch Discord x-fingerprint from /experiments, or use a pre-harvested one."""
    # Try pre-harvested fingerprint first
    load_custom_fingerprints()
    custom_fp = pop_custom_fingerprint()
    if custom_fp:
        _file_log(f"[FP] Using custom fingerprint: {custom_fp[:36]}...")
        return custom_fp
    headers = {
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "accept-encoding": "gzip, deflate, br",
        "accept-language": f"{session_profile['lang']},en;q=0.9",
        "sec-ch-ua": session_profile["sec_ch_ua"],
        "sec-ch-ua-mobile": session_profile["sec_ch_ua_mobile"],
        "sec-ch-ua-platform": session_profile["sec_ch_ua_platform"],
        "sec-fetch-dest": "document",
        "sec-fetch-mode": "navigate",
        "sec-fetch-site": "none",
        "sec-fetch-user": "?1",
        "upgrade-insecure-requests": "1",
        "user-agent": session_profile["ua"]
    }
    session.headers.update(headers)
    data = session.get("https://discord.com/api/v9/experiments")
    payload = data.json()
    fp = payload.get("fingerprint") if isinstance(payload, dict) else None
    if not fp:
        raise RuntimeError(f"experiments missing fingerprint [{data.status_code}]: {str(payload)[:200]}")
    return fp
def build_headers(fingerprint, super_props, session_profile):
    """Build Discord API headers using profile-specific values."""
    return {
        "accept": "*/*",
        "accept-encoding": "gzip, deflate, br, zstd",
        "accept-language": f"{session_profile['lang']},en;q=0.9",
        "content-type": "application/json",
        "origin": "https://discord.com",
        "referer": "https://discord.com/",
        "priority": "u=1, i",
        "sec-ch-ua": session_profile["sec_ch_ua"],
        "sec-ch-ua-mobile": session_profile["sec_ch_ua_mobile"],
        "sec-ch-ua-platform": session_profile["sec_ch_ua_platform"],
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "user-agent": session_profile["ua"],
        "x-debug-options": "bugReporterEnabled",
        "x-discord-locale": session_profile["lang"],
        "x-discord-timezone": session_profile["timezone"],
        "x-fingerprint": fingerprint,
        "x-super-properties": super_props,
        "x-context-properties": context_properties(),
    }
def context_properties(location="Register"):
    """Build x-context-properties header value."""
    raw = json.dumps({"location": location}, separators=(",", ":")).encode()
    return base64.b64encode(raw).decode()
def verify_token_integrity(session):
    try:
        r = session.get("https://discord.com/api/v9/users/@me")
        if r.status_code != 200:
            return "invalid"
        r2 = session.get("https://discord.com/api/v9/users/@me/settings")
        if r2.status_code == 200:
            return "Valid"
        elif r2.status_code == 403:
            return "locked"
    except Exception:
        pass
    return "invalid"
def export_credential(email, password, token, token_status, is_verified=False, is_humanized=False):
    os.makedirs("output", exist_ok=True)
    status_lower = token_status.lower() if token_status else ""
    if "locked" in status_lower:
        filename = "output/locked.txt"
    elif "invalid" in status_lower:
        filename = "output/invalid.txt"
    elif is_humanized:
        filename = "output/humanised.txt"
    elif is_verified:
        filename = "output/email_verified.txt"
    else:
        filename = "output/tokens.txt"
    with open(filename, "a", encoding="utf-8") as f:
        f.write(f"{email}:{password}:{token}\n")
class WebSocketClientKeepAlive:
    
    def __init__(self, token):
        self.token = token
        self._stop = threading.Event()
        self._thread = None
    def start(self):
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
    def stop(self):
        self._stop.set()
    def _run(self):
        try:
            ws = websocket.WebSocket()
            ws.settimeout(10)
            ws.connect("wss://gateway.discord.gg/?v=9&encoding=json")
            hello = json.loads(ws.recv())
            heartbeat_interval = hello["d"]["heartbeat_interval"] / 1000
            identify = {
                "op": 2,
                "d": {
                    "token": self.token,
                    "capabilities": 16381,
                    "properties": {
                        "os": "Windows",
                        "browser": "Chrome",
                        "device": "",
                        "system_locale": "en-US",
                        "browser_user_agent": random.choice(USER_AGENTS),
                        "browser_version": "136.0.0.0",
                        "os_version": "10",
                        "referrer": "https://discord.com/",
                        "referring_domain": "discord.com",
                        "referrer_current": "",
                        "referring_domain_current": "",
                        "release_channel": "stable",
                        "client_build_number": get_build_number(),
                        "client_event_source": None,
                    },
                    "presence": {
                        "status": "online",
                        "since": 0,
                        "activities": [],
                        "afk": False
                    },
                    "compress": False,
                    "client_state": {
                        "guild_versions": {},
                        "highest_last_message_id": "0",
                        "read_state_version": 0,
                        "user_guild_settings_version": -1,
                        "user_settings_version": -1,
                        "private_channels_version": "0",
                        "api_code_version": 0
                    }
                },
            }
            ws.send(json.dumps(identify))
            ready = False
            for _ in range(10):
                resp = json.loads(ws.recv())
                if resp.get("t") == "READY":
                    ready = True
                    break
                if resp.get("op") == 9:  
                    ws.close()
                    return
            if not ready:
                ws.close()
                return
            while not self._stop.is_set():
                ws.send(json.dumps({"op": 1, "d": None}))
                self._stop.wait(heartbeat_interval)
            ws.close()
        except Exception:
            pass
def process_hcaptcha(sitekey, rqdata, user_agent, proxy=None,
                     session_profile=None, discord_fingerprint=None,
                     cookies=None, super_props=None,
                     captcha_rqtoken=None, captcha_session_id=None,
                     url="https://discord.com/register"):
    """Solve hCaptcha with full session context forwarding."""
    solver_key = config.get("9captcha", {}).get("api_key", "")
    solver = Solver(
        url=url,
        sitekey=sitekey,
        rqdata=rqdata,
        user_agent=user_agent,
        proxy=proxy,
        api_key=solver_key,
        session_profile=session_profile,
        discord_fingerprint=discord_fingerprint,
        cookies=cookies,
        super_props=super_props,
        captcha_rqtoken=captcha_rqtoken,
        captcha_session_id=captcha_session_id,
    )
    return solver.solve()
def generate_apzx_token(email, username, password, proxy=None, current_num=1, mail_api=None, mail_provider_name=None, use_local_ip=False):
    Log.proxy_header(current_num, proxy)
    Log.status(f"Got User -> {username}")
    Log.status(f"Got Pass -> {password}")
    email = email.lower()
    masked_mail = f"{email[:4]}***@{email.split('@')[1]}" if '@' in email else email
    Log.status(f"Got Mail -> {masked_mail}")
    
    if not mail_api:
        mail_api, mail_provider_name = get_mail_provider()
        if not mail_api:
            mail_api = APZMailApi(logger=print)
            mail_provider_name = "cybertemp (fallback)"
        
    session = StealthSession()
    if proxy:
        px = parse_proxy(proxy)
        if px: session.proxies = {"http": px, "https": px}
    # Use a realistic browser fingerprint profile instead of random UA
    sp = resolve_session_profile()
    user_agent = sp["ua"]
    chrome_version = sp["chrome_version"]
    Log.status(f"Profile → {sp['name']}")
    try:
        dcfduid, sdcfduid = acquire_discord_cookies(session)
        fingerprint = fetch_discord_fingerprint(session, dcfduid, sdcfduid, sp)
    except Exception as e:
        err_str = str(e).lower()
        if "timeout" in err_str or "(28)" in err_str or "(56)" in err_str or "connection reset" in err_str or "(35)" in err_str or "tls connect" in err_str:
            print(f"  \033[33m⚠ WARNING: Proxy dropped connection or timed out. Moving to next proxy...\033[0m")
        else:
            Log.error(f"fingerprint failed: {e}")
        return
    build_num = get_build_number(proxy)
    super_props = build_super_properties(build_num, sp)
    headers = build_headers(fingerprint, super_props, sp)
    session.headers.update(headers)
    dob = _random_dob()
    Log.status(f"Got DOB -> {dob}")
    time.sleep(random.uniform(2, 5))
    if True:
        dumb_domain = random.choice(["@gmail.com", "@baldur.edu.kg", "duckmail.sbs"])
        dumb_email = f"{username}{random.randint(100, 99999)}{dumb_domain}"
        fake_payload = {
            "fingerprint": fingerprint,
            "email": dumb_email,
            "username": username,
            "password": password,
            "date_of_birth": dob,
            "consent": True,
        }

        try:
            session.post("https://discord.com/api/v9/auth/register", json=fake_payload)
        except Exception:
            pass

    # Normal registration payload flow

    register_payload = {
        "fingerprint": fingerprint,
        "email": email,
        "username": username,
        "password": password,
        "invite": None,
        "date_of_birth": dob,
        "consent": True,
        "promotional_email_opt_in": False,
        "gift_code_sku_id": None,
    }
    Log.status("Creating Acc..")
    try: _debug_log(f"[REGISTER] First POST to /auth/register")
    except: pass
    try: _debug_log(f"[REGISTER] Headers: {dict(session.headers)}")
    except: pass
    try: _debug_log(f"[REGISTER] Body: {json.dumps(register_payload, separators=(',',':'))}")
    except: pass
    try:
        res = session.post("https://discord.com/api/v9/auth/register", json=register_payload)
        start_time = time.time()
        res_json = res.json()
        try: _debug_log(f"[REGISTER] First POST response [{res.status_code}]: {json.dumps(res_json, separators=(',',':'))[:500]}")
        except: pass
        if res.status_code == 429:
            Log.error(f"Rate limited by Discord. (Warp IPs are shared and heavily banned. Use Residential Proxies for 0 rate limits!)")
            return
    except Exception as e:
        Log.error(f"Network error during registration (proxy timeout/dead): {e}")
        return
    captcha_sitekey = res_json.get("captcha_sitekey")
    captcha_rqdata = res_json.get("captcha_rqdata")
    captcha_rqtoken = res_json.get("captcha_rqtoken")
    captcha_session_id = res_json.get("captcha_session_id")
    try: _debug_log(f"[REGISTER] captcha_sitekey={captcha_sitekey}, rqdata={'SET' if captcha_rqdata else 'MISSING'}, rqtoken={captcha_rqtoken}, session_id={captcha_session_id}")
    except: pass
    if not captcha_sitekey or not captcha_rqdata:
        if "token" in res_json:
            Log.status("Account created without captcha!")
            # The logic below expects a cap_token, but if we got a token early we should handle it
            pass
        else:
            err_msg = "Unknown Rate Limit or Global Ban"
            try:
                errors = res_json.get('errors', {})
                if 'username' in errors and '_errors' in errors['username']:
                    for e in errors['username']['_errors']:
                        if e.get('code') == 'USERNAME_ALREADY_TAKEN':
                            err_msg = "Name Taken"
                            break
            except Exception:
                pass
            Log.error(f"Registration Blocked: {err_msg}")
            return
    Log.solving(email)
    captcha_start = time.time()
        
    if captcha_rqdata:
        Log.status(f"Attaching RQDATA ({len(captcha_rqdata)} bytes) to solver payload...")
    else:
        Log.error("FATAL: Discord did not provide rqdata!")
    
    # Get current session cookies to forward to solver
    session_cookies = {}
    try:
        session_cookies = session.cookies.get_dict()
    except Exception:
        pass
    cap_token, cookies = process_hcaptcha(
        captcha_sitekey, captcha_rqdata, user_agent, proxy=proxy,
        session_profile=sp, discord_fingerprint=fingerprint,
        cookies=session_cookies, super_props=super_props,
        captcha_rqtoken=captcha_rqtoken, captcha_session_id=captcha_session_id,
    )
    if cap_token == "ERROR_RATELIMIT":
        Log.error("ip/proxy ratelimited by hCaptcha")
        return
    if cap_token == "ERROR_IP_REJECTED":
        Log.error("ip/proxy rejected by hCaptcha — your IP was flagged. Try a different proxy or use Extension solver.")
        return
    if not cap_token:
        Log.captcha_failed()
        return
    if cookies:
        for k, v in cookies.items():
            session.cookies.set(k, v)
    solve_time = time.time() - captcha_start
    Log.captcha_solved(solve_time, cap_token)
    # Build body with captcha tokens (Discord now expects them in JSON body)
    body_payload = dict(register_payload)
    body_payload["gwid"] = ""
    if captcha_rqtoken:
        body_payload["captcha_rqtoken"] = captcha_rqtoken
    if captcha_session_id:
        body_payload["captcha_session_id"] = captcha_session_id
    if captcha_rqdata:
        body_payload["captcha_rqdata"] = captcha_rqdata
    body_payload["gift_code_sku_id"] = None

    session.headers.update({
        "x-captcha-key": cap_token,
        "x-captcha-rqtoken": captcha_rqtoken,
        "x-captcha-session-id": captcha_session_id,
    })
    try: _debug_log(f"[REGISTER] Second POST (with captcha) — Body: {json.dumps(body_payload, separators=(',',':'))[:600]}")
    except: pass
    try: _debug_log(f"[REGISTER] Second POST (with captcha) — Headers: {dict(session.headers)}")
    except: pass
    if use_local_ip:
        Log.status(f"[Local IP] Generating with direct IP (no proxy)")
    response = None
    for attempt in range(3):
        try:
            response = session.post("https://discord.com/api/v9/auth/register", json=body_payload)
            try: _debug_log(f"[REGISTER] Attempt {attempt+1} response [{response.status_code}]: {response.text[:500]}")
            except: pass
            if response.status_code != 400 or 'token' in response.json():
                break
            # Captcha invalid - re-solve
            cap_token, cookies = process_hcaptcha(
                captcha_sitekey, captcha_rqdata, user_agent, proxy=proxy,
                session_profile=sp, discord_fingerprint=fingerprint,
                cookies=session_cookies, super_props=super_props,
                captcha_rqtoken=captcha_rqtoken, captcha_session_id=captcha_session_id,
            )
            session.headers["x-captcha-key"] = cap_token
            try: _debug_log(f"[REGISTER] Re-solved captcha for attempt {attempt+2}")
            except: pass
        except Exception as e:
            if attempt < 2:
                time.sleep(1)
            else:
                return
    try:
        raw_text = response.text
    except Exception as e:
        Log.error(f"Failed to read raw response: {e}")
    try:
        res_data = response.json()
    except Exception:
        Log.error("Response is not valid JSON")
        try: _debug_log(f"[REGISTER] Non-JSON response [{response.status_code}]: {response.text[:500]}")
        except: pass
        return
    if 'token' not in res_data:
        err_str = "Registration Blocked"
        status_code = response.status_code
        raw_err = response.text[:500]
        if res_data.get('captcha_key') == ['invalid-response']:
            err_str = "Discord Rejected Captcha Token (invalid-response)"
            Log.error(f"Captcha invalid-response. Raw: {raw_err}")
        elif res_data.get('message'):
            err_str = res_data.get('message')
            Log.error(f"Discord API error ({status_code}): {err_str}")
        else:
            Log.error(f"Account Finalization Failed ({status_code}): {res_data}")
        try: _debug_log(f"[REGISTER] FINAL ERROR [{status_code}]: {raw_err}")
        except: pass
        try: _debug_log(f"[REGISTER] FULL JSON: {response.text[:1000]}")
        except: pass
        return
    auth_token = res_data['token']
    for h in ["x-captcha-key", "x-captcha-rqtoken", "x-captcha-session-id"]:
        session.headers.pop(h, None)
    session.headers.update({"authorization": auth_token})
    Log.status("Token Received...")
    time.sleep(random.uniform(3, 6))
    onliner = WebSocketClientKeepAlive(auth_token)
    onliner.start()
    if not verification_enabled:
        pre_verify_status = verify_token_integrity(session)
        is_humanized = False
        if config.get("humanizer", {}).get("enabled", False) and pre_verify_status.lower() == "valid":
            Log.status("starting humanizer")
            try:
                name_list = load_file_lines(NAMES_FILE)
                bio_list = load_file_lines(BIOS_FILE)
                pronouns_list = load_file_lines(PRONOUNS_FILE)
                av_files = load_avatar_files()
                hz = Humanizer(auth_token, proxy)
                success = hz.process(name_list, bio_list, pronouns_list, av_files, load_avatar_as_base64)
                if success:
                    hz_cfg = config.get("humanizer", {})
                    fields = []
                    if hz_cfg.get("bio"): fields.append(f"Bio {Fore.GREEN}✓{Style.RESET_ALL}{Fore.MAGENTA}")
                    if hz_cfg.get("pronouns"): fields.append(f"Pronouns {Fore.GREEN}✓{Style.RESET_ALL}{Fore.MAGENTA}")
                    if hz_cfg.get("hypesquad"): fields.append(f"HypeSquad {Fore.GREEN}✓{Style.RESET_ALL}{Fore.MAGENTA}")
                    if hz_cfg.get("avatar"): fields.append(f"Avatar {Fore.GREEN}✓{Style.RESET_ALL}{Fore.MAGENTA}")
                    if hz_cfg.get("display_name"): fields.append(f"Name {Fore.GREEN}✓{Style.RESET_ALL}{Fore.MAGENTA}")
                    hz_str = " ".join(fields)
                    Log.status(f"humanized {hz_str}")
                    is_humanized = True
            except Exception as e:
                Log.error(f"humaniser module failed: {e}")
        export_credential(email, password, auth_token, pre_verify_status, is_verified=False, is_humanized=is_humanized)
        onliner.stop()
        return
    Log.waiting("waiting for verification email...")
    verify_url = mail_api.get_verify_url(email, 3, 180, proxy)
    if not verify_url:
        Log.error("verification email never arrived — saving as-is")
        token_status = verify_token_integrity(session)
        Log.status(f"Token status: {token_status.upper()}")
        export_credential(email, password, auth_token, token_status)
        onliner.stop()
        return
    Log.status("Got verify URL...")
    try:
        click_headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-language': f"{sp['lang']},en;q=0.9",
            'sec-ch-ua': sp['sec_ch_ua'],
            'sec-ch-ua-mobile': sp['sec_ch_ua_mobile'],
            'sec-ch-ua-platform': sp['sec_ch_ua_platform'],
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'none',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': user_agent,
        }
        mail_token = None
        if "token=" in verify_url:
            mail_token = verify_url.split("token=")[-1].split("&")[0]
        if not mail_token:
            location = ""
            r1 = session.get(verify_url, headers=click_headers, allow_redirects=False)
            location = r1.headers.get("Location", "")
            if location:
                fragment = urlparse(location).fragment
                if fragment and "token=" in fragment:
                    mail_token = fragment.split("token=")[-1].split("&")[0]
            if not mail_token and location:
                r2 = session.get(location, headers=click_headers, allow_redirects=False)
                location2 = r2.headers.get("Location", "")
                if location2:
                    fragment2 = urlparse(location2).fragment
                    if fragment2 and "token=" in fragment2:
                        mail_token = fragment2.split("token=")[-1].split("&")[0]
        if not mail_token:
            token_status = verify_token_integrity(session)
            export_credential(email, password, auth_token, token_status)
            onliner.stop()
            return
    except Exception:
        token_status = verify_token_integrity(session)
        export_credential(email, password, auth_token, token_status)
        onliner.stop()
        return
    for h in ["x-captcha-key", "x-captcha-rqtoken", "x-captcha-session-id"]:
        session.headers.pop(h, None)
    time.sleep(random.uniform(1, 3))
    verify_res = session.post(
        "https://discord.com/api/v9/auth/verify",
        json={"token": mail_token}
    )
    verify_json = verify_res.json()
    if verify_json.get("captcha_sitekey"):
        Log.solving(email)
        verify_start = time.time()
        verify_cap_token, verify_cookies = process_hcaptcha(
            verify_json["captcha_sitekey"],
            verify_json.get("captcha_rqdata", ""),
            user_agent,
            proxy=proxy,
            session_profile=sp, discord_fingerprint=fingerprint,
            cookies=session_cookies, super_props=super_props,
            captcha_rqtoken=verify_json.get("captcha_rqtoken", ""),
            captcha_session_id=verify_json.get("captcha_session_id", ""),
            url="https://discord.com/api/v9/auth/verify",
        )
        if not verify_cap_token:
            Log.captcha_failed()
            token_status = verify_token_integrity(session)
            export_credential(email, password, auth_token, token_status)
            onliner.stop()
            return
        verify_solve_time = time.time() - verify_start
        Log.captcha_solved(verify_solve_time, verify_cap_token)
        if verify_cookies:
            for k, v in verify_cookies.items():
                session.cookies.set(k, v)
        session.headers.update({
            "x-captcha-key": verify_cap_token,
            "x-captcha-rqtoken": verify_json.get("captcha_rqtoken", ""),
            "x-captcha-session-id": verify_json.get("captcha_session_id", ""),
        })
        verify_res = session.post(
            "https://discord.com/api/v9/auth/verify",
            json={"token": mail_token}
        )
        verify_json = verify_res.json()
    new_token = verify_json.get("token")
    if new_token:
        auth_token = new_token
        session.headers.update({"authorization": auth_token})
        Log.verified(auth_token)
    else:
        Log.error(f"Verification response had no token: {str(verify_json)[:200]}")
    for h in ["x-captcha-key", "x-captcha-rqtoken", "x-captcha-session-id"]:
        session.headers.pop(h, None)
    token_status = verify_token_integrity(session)
    Log.status(f"Final status: {token_status.upper()}")
    is_humanized = False
    if config.get("humanizer", {}).get("enabled", False) and token_status.lower() == "valid":
        Log.status("starting humanizer")
        try:
            name_list = load_file_lines(NAMES_FILE)
            bio_list = load_file_lines(BIOS_FILE)
            pronouns_list = load_file_lines(PRONOUNS_FILE)
            av_files = load_avatar_files()
            hz = Humanizer(auth_token, proxy)
            success = hz.process(name_list, bio_list, pronouns_list, av_files, load_avatar_as_base64)
            if success:
                hz_cfg = config.get("humanizer", {})
                fields = []
                if hz_cfg.get("bio"): fields.append(f"Bio {Fore.GREEN}✓{Style.RESET_ALL}{Fore.MAGENTA}")
                if hz_cfg.get("pronouns"): fields.append(f"Pronouns {Fore.GREEN}✓{Style.RESET_ALL}{Fore.MAGENTA}")
                if hz_cfg.get("hypesquad"): fields.append(f"HypeSquad {Fore.GREEN}✓{Style.RESET_ALL}{Fore.MAGENTA}")
                if hz_cfg.get("avatar"): fields.append(f"Avatar {Fore.GREEN}✓{Style.RESET_ALL}{Fore.MAGENTA}")
                if hz_cfg.get("display_name"): fields.append(f"Name {Fore.GREEN}✓{Style.RESET_ALL}{Fore.MAGENTA}")
                hz_str = " ".join(fields)
                Log.status(f"humanized {hz_str}")
                is_humanized = True
        except Exception as e:
            Log.error(f"humaniser module failed: {e}")
    export_credential(email, password, auth_token, token_status, is_verified=True, is_humanized=is_humanized)
    onliner.stop()
    pass
from pathlib import Path
SCRIPT_DIR = Path(__file__).resolve().parent
_async_loop = asyncio.new_event_loop()
_async_loop_thread = threading.Thread(target=_async_loop.run_forever, daemon=True)
_async_loop_thread.start()
SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR / "engine" / "data"
INPUT_DIR = SCRIPT_DIR / "engine" / "input"
AVATARS_DIR = SCRIPT_DIR / "engine" / "avatar"
BANNERS_DIR = SCRIPT_DIR / "engine" / "banners"
TOKENS_FILE = INPUT_DIR / "tokens.txt"
PROXIES_FILE = INPUT_DIR / "proxies.txt"
BIOS_FILE = DATA_DIR / "bios.txt"
NAMES_FILE = DATA_DIR / "names.txt"
PRONOUNS_FILE = DATA_DIR / "pronouns.txt"
SUCCESS_FILE = INPUT_DIR / "success.txt"
FAILED_FILE = INPUT_DIR / "failed.txt"
hz_config = config.get("humanizer", {})
MAX_THREADS = config.get("threading", {}).get("humanizer", config.get("humanizer", {}).get("max_threads", 3))
AVATAR_DIMENSION = hz_config.get("avatar_dimension", 256)
MAX_AVATAR_CACHE = hz_config.get("max_avatar_cache", 100)
UPDATE_DISPLAY_NAME = hz_config.get("display_name", True)
UPDATE_BIO = hz_config.get("bio", True)
UPDATE_PRONOUNS = hz_config.get("pronouns", True)
UPDATE_AVATAR = hz_config.get("avatar", True)
UPDATE_HYPESQUAD = hz_config.get("hypesquad", True)
RETRY_LIMIT = hz_config.get("retries", 3)
HYPESQUAD_HOUSES = {
    1: "Bravery",
    2: "Brilliance",
    3: "Balance"
}
DISCORD_API = "https://discord.com/api/v9"
DISCORD_GATEWAY = "wss://gateway.discord.gg/?v=9&encoding=json"
FALLBACK_BUILD_NUMBER = 519006
DISCORD_CLIENT_VERSION = "1.0.9171"
ELECTRON_VERSION = "34.5.1"
CHROME_VERSION_ELECTRON = "132"
DEFAULT_USER_AGENT = (
    f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    f"(KHTML, like Gecko) discord/{DISCORD_CLIENT_VERSION} "
    f"Chrome/{CHROME_VERSION_ELECTRON}.0.0.0 Electron/{ELECTRON_VERSION} Safari/537.36"
)
def fetch_build_number() -> int:
    try:
        resp = primp.Client(verify=False).get("https://discord.com/login", timeout=10)
        if resp.status_code != 200:
            return FALLBACK_BUILD_NUMBER
        asset_urls = re.findall(r'/assets/([a-zA-Z0-9_-]+)\.js', resp.text)
        if not asset_urls:
            return FALLBACK_BUILD_NUMBER
        for asset_hash in reversed(asset_urls):
            try:
                js_resp = primp.Client(verify=False).get(
                    f"https://discord.com/assets/{asset_hash}.js",
                    timeout=10
                )
                if js_resp.status_code != 200:
                    continue
                match = re.search(r'buildNumber["\s:,]+(\d{4,7})', js_resp.text)
                if match:
                    return int(match.group(1))
            except Exception:
                continue
        return FALLBACK_BUILD_NUMBER
    except Exception:
        return FALLBACK_BUILD_NUMBER
BUILD_NUMBER = fetch_build_number()
def _random_uuid() -> str:
    return f"{random.randint(10000000, 99999999)}-{random.randint(1000, 9999)}-{random.randint(1000, 9999)}-{random.randint(1000, 9999)}-{random.randint(100000000000, 999999999999)}"
def generate_super_properties(
    launch_id: str, signature: str, heartbeat_id: str, native_build: int
) -> str:
    return base64.b64encode(json.dumps({
        "os": "Windows",
        "browser": "Discord Client",
        "release_channel": "stable",
        "client_version": DISCORD_CLIENT_VERSION,
        "os_version": "10.0.26100",
        "os_arch": "x64",
        "app_arch": "x64",
        "system_locale": "en-US",
        "has_client_mods": False,
        "browser_user_agent": DEFAULT_USER_AGENT,
        "browser_version": ELECTRON_VERSION,
        "client_build_number": BUILD_NUMBER,
        "native_build_number": native_build,
        "client_event_source": None,
        "client_launch_id": launch_id,
        "launch_signature": signature,
        "client_heartbeat_session_id": heartbeat_id,
    }, separators=(",", ":")).encode()).decode()
hz_proxy_manager = None
print_lock = threading.Lock()
file_lock = threading.Lock()
def get_timestamp() -> str:
    return datetime.now().strftime("%H:%M:%S")
def log(log_type: str, token: str, message: str):
    timestamp = get_timestamp()
    masked = mask_token(token)
    with print_lock:
        ts = f"{Fore.LIGHTBLACK_EX}[{timestamp}]{Style.RESET_ALL}"
        tok = f"{Fore.LIGHTBLACK_EX}[{Style.RESET_ALL}Token : {Fore.CYAN}{masked}{Style.RESET_ALL}{Fore.LIGHTBLACK_EX}]{Style.RESET_ALL}"
        if log_type == "SUCCESS":
            status = f"{Fore.GREEN}[SUCCESS]{Style.RESET_ALL}"
        elif log_type == "FAILED":
            status = f"{Fore.RED}[FAILED]{Style.RESET_ALL}"
        elif log_type == "WARN":
            status = f"{Fore.YELLOW}[WARN]{Style.RESET_ALL}"
        elif log_type == "INFO":
            status = f"{Fore.CYAN}[INFO]{Style.RESET_ALL}"
        else:
            status = f"[{log_type}]"
        if " : " in message and message.startswith("[") and message.endswith("]"):
            inner = message[1:-1]
            parts = inner.split(" : ", 1)
            if len(parts) == 2:
                desc, value = parts
                msg = f"{Fore.LIGHTBLACK_EX}[{Style.RESET_ALL}{Fore.WHITE}{desc}{Style.RESET_ALL} : {Fore.CYAN}{value}{Style.RESET_ALL}{Fore.LIGHTBLACK_EX}]{Style.RESET_ALL}"
            else:
                msg = f"{Fore.LIGHTBLACK_EX}[{Style.RESET_ALL}{Fore.WHITE}{inner}{Style.RESET_ALL}{Fore.LIGHTBLACK_EX}]{Style.RESET_ALL}"
        else:
            msg = message
        print(f"{ts} - {status} - {tok} → {msg}")
def log_simple(log_type: str, message: str):
    timestamp = get_timestamp()
    ts = f"{Fore.LIGHTBLACK_EX}[{timestamp}]{Style.RESET_ALL}"
    with print_lock:
        if log_type == "FAILED":
            print(f"{ts} - {Fore.RED}[FAILED]{Style.RESET_ALL} - {Fore.RED}{message}{Style.RESET_ALL}")
        elif log_type == "INFO":
            print(f"{ts} - {Fore.CYAN}[INFO]{Style.RESET_ALL} - {Fore.WHITE}{message}{Style.RESET_ALL}")
        else:
            print(f"{ts} - {message}")
def mask_token(token: str) -> str:
    if len(token) <= 20:
        return token[:10] + "****"
    return token[:10] + "****" + token[-10:]
def load_file_lines(file_path: Path) -> List[str]:
    if not file_path.exists():
        return []
    with open(file_path, 'r', encoding='utf-8') as f:
        return [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]
def append_to_file(file_path: Path, content: str):
    with file_lock:
        with open(file_path, 'a', encoding='utf-8') as f:
            f.write(content + '\n')
def remove_token_from_file(file_path: Path, token: str):
    with file_lock:
        try:
            lines = file_path.read_text(encoding='utf-8').splitlines()
            new_lines = [l for l in lines if extract_token(l) != token.strip()]
            file_path.write_text('\n'.join(new_lines) + ('\n' if new_lines else ''), encoding='utf-8')
        except Exception:
            pass 
def format_time(seconds: float) -> str:
    minutes = int(seconds // 60)
    hours = minutes // 60
    if hours > 0:
        return f"{hours}h {minutes % 60}m"
    if minutes > 0:
        secs = seconds % 60
        return f"{minutes}m {secs:.2f}s"
    return f"{seconds:.2f}s"
def is_valid_token(s: str) -> bool:
    if not s or len(s) < 50:
        return False
    parts = s.split('.')
    if len(parts) != 3:
        return False
    return all(re.match(r'^[A-Za-z0-9_-]+$', part) and len(part) > 0 for part in parts)
def extract_token(line: str) -> Optional[str]:
    line = line.strip()
    if not line:
        return None
    if is_valid_token(line):
        return line
    for delimiter in [':', '|', '\t', ' ']:
        if delimiter in line:
            parts = line.split(delimiter)
            for part in reversed(parts):
                part = part.strip()
                if is_valid_token(part):
                    return part
    return None
def load_tokens(file_path: Path) -> List[str]:
    lines = load_file_lines(file_path)
    tokens = []
    for line in lines:
        token = extract_token(line)
        if token:
            tokens.append(token)
    seen = set()
    deduped = []
    for t in tokens:
        if t not in seen:
            seen.add(t)
            deduped.append(t)
    return deduped
def load_avatar_files() -> List[Path]:
    if not AVATARS_DIR.exists():
        return []
    valid_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.webp'}
    return [f for f in AVATARS_DIR.iterdir() if f.suffix.lower() in valid_extensions]
DISCORD_AVATAR_MAX_BYTES = 1_000_000  
def load_avatar_as_base64(image_path: Path) -> Optional[str]:
    try:
        with Image.open(image_path) as img:
            is_png = image_path.suffix.lower() == '.png'
            if is_png:
                if img.mode == 'P':
                    img = img.convert('RGBA')
            else:
                if img.mode in ('RGBA', 'P'):
                    img = img.convert('RGB')
            img = img.resize((AVATAR_DIMENSION, AVATAR_DIMENSION), Image.Resampling.LANCZOS)
            img_copy = img.copy()  
            def _encode(pil_img, fmt, quality=80) -> str:
                buf = BytesIO()
                kw = {"format": fmt}
                if fmt == "JPEG":
                    kw["quality"] = quality
                    kw["optimize"] = True
                pil_img.save(buf, **kw)
                buf.seek(0)
                return base64.b64encode(buf.read()).decode()
            img_format = 'PNG' if is_png else 'JPEG'
            b64 = _encode(img_copy, img_format)
            mime = 'image/png' if img_format == 'PNG' else 'image/jpeg'
            if len(b64) > DISCORD_AVATAR_MAX_BYTES:
                work_img = img_copy.convert('RGB') if img_copy.mode in ('RGBA', 'P', 'LA') else img_copy
                mime = 'image/jpeg'
                for quality in (80, 60, 40, 20):
                    b64 = _encode(work_img, 'JPEG', quality)
                    if len(b64) <= DISCORD_AVATAR_MAX_BYTES:
                        break
                else:
                    half = max(64, AVATAR_DIMENSION // 2)
                    work_img = work_img.resize((half, half), Image.Resampling.LANCZOS)
                    for quality in (80, 60, 40):
                        b64 = _encode(work_img, 'JPEG', quality)
                        if len(b64) <= DISCORD_AVATAR_MAX_BYTES:
                            break
                    else:
                        return None  
            return f"data:{mime};base64,{b64}"
    except Exception:
        return None
def parse_proxy(proxy_string: str) -> Optional[str]:
    proxy = proxy_string.strip()
    if proxy.startswith('#'):
        return None
    if '://' in proxy:
        parsed = urlparse(proxy)
        if parsed.hostname and parsed.port:
            return proxy
        return None
    if '@' in proxy:
        # Format: user:pass@host:port
        try:
            auth, host_port = proxy.split('@')
            user, password = auth.split(':', 1)
            host, port = host_port.split(':', 1)
            return f"http://{quote(user, safe='')}:{quote(password, safe='')}@{host}:{port}"
        except Exception:
            return None
    
    # Format: host:port:user:pass
    parts = proxy.split(":")
    if len(parts) == 4:
        host, port, user, password = parts
        return f"http://{quote(user, safe='')}:{quote(password, safe='')}@{host}:{port}"
    elif len(parts) == 2:
        return f"http://{parts[0]}:{parts[1]}"
    return None

class Humanizer:
    def __init__(self, token: str, proxy: Optional[str] = None):
        self.token = token
        self.proxy = proxy
        self.client = primp.Client(
            verify=False,
            proxy=parse_proxy(proxy) if proxy else None
        )
        self.user_agent = DEFAULT_USER_AGENT
        self.session_id = None
        self.proxy_failed = False
        self.is_locked = False
        self.installation_id = f"{random.randint(10**18, 10**19 - 1)}.{''.join(random.choices('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_', k=22))}"
        self._launch_id = str(uuid.uuid4())
        self._signature = str(uuid.uuid4())
        self._heartbeat_id = str(uuid.uuid4())
        self._native_build = random.randint(65600, 65800)
        self._super_props = generate_super_properties(
            self._launch_id, self._signature, self._heartbeat_id, self._native_build
        )
    def get_fingerprint(self):
        try:
            r = self.client.get("https://discord.com/api/v9/experiments", timeout=30)
            if r.status_code == 200:
                return r.json().get("fingerprint")
        except:
            pass
        return None
    async def _send_identify(self, ws) -> bool:
        try:
            hello = json.loads(await asyncio.wait_for(ws.recv(), timeout=15))
            if hello.get("op") != 10:
                return False
            identify_payload = {
                "op": 2,
                "d": {
                    "token": self.token,
                    "capabilities": 16381,
                    "properties": {
                        "os": "Windows",
                        "browser": "Discord Client",
                        "release_channel": "stable",
                        "client_version": DISCORD_CLIENT_VERSION,
                        "os_version": "10.0.26100",
                        "os_arch": "x64",
                        "app_arch": "x64",
                        "system_locale": "en-US",
                        "browser_user_agent": self.user_agent,
                        "browser_version": ELECTRON_VERSION,
                        "os_sdk_version": "26100",
                        "client_build_number": BUILD_NUMBER,
                        "native_build_number": self._native_build,
                        "client_event_source": None,
                        "design_id": 0
                    },
                    "presence": {
                        "status": "online",
                        "since": 0,
                        "activities": [],
                        "afk": False
                    },
                    "compress": False,
                    "client_state": {
                        "guild_versions": {},
                        "highest_last_message_id": "0",
                        "read_state_version": 0,
                        "user_guild_settings_version": -1,
                        "user_settings_version": -1,
                        "private_channels_version": "0",
                        "api_code_version": 0
                    }
                }
            }
            await ws.send(json.dumps(identify_payload))
            return True
        except Exception:
            return False
    async def _wait_for_ready(self, ws) -> bool:
        for _ in range(12):     
            try:
                msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=10))
                op = msg.get("op")
                t = msg.get("t")
                if op == 11 or (op == 0 and t != "READY"):
                    continue
                if t == "READY":
                    self.session_id = msg["d"].get("session_id")
                    return True
                if op == 9:
                    return False
            except asyncio.TimeoutError:
                break
        return False
    async def update_account_with_live_session(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        if getattr(self, "is_locked", False):
            return {"success": False, "error": "Token Locked"}
        headers = self.get_headers()
        loop = asyncio.get_event_loop()
        if "avatar" not in payload:
            direct = await loop.run_in_executor(None, lambda: self.update_user_profile(payload, headers))
            if direct.get("success") or direct.get("captcha") or direct.get("rate_limited"):
                return direct
            if not direct.get("unknown_session"):
                return direct
        async def _ws_patch(ws) -> Dict[str, Any]:
            if not await self._send_identify(ws):
                return {"success": False, "error": "Gateway IDENTIFY failed"}
            if not await self._wait_for_ready(ws):
                return {"success": False, "error": "Gateway READY timeout"}
            return await loop.run_in_executor(None, lambda: self.update_user_profile(payload, headers))
        try:
            extra_headers = {"User-Agent": self.user_agent}
            if self.proxy:
                parsed_px = parse_proxy(self.proxy)
                if not parsed_px:
                    return {"success": False, "error": "Invalid proxy string"}
                proxy = Proxy.from_url(parsed_px)
                sock = await proxy.connect(dest_host="gateway.discord.gg", dest_port=443)
                async with websockets.connect(
                    DISCORD_GATEWAY,
                    additional_headers=extra_headers,
                    sock=sock,
                    server_hostname="gateway.discord.gg",
                    open_timeout=60,
                    close_timeout=10,
                    max_size=None   
                ) as ws:
                    return await _ws_patch(ws)
            else:
                async with websockets.connect(
                    DISCORD_GATEWAY,
                    additional_headers=extra_headers,
                    open_timeout=60,
                    close_timeout=10,
                    max_size=None   
                ) as ws:
                    return await _ws_patch(ws)
        except Exception as e:
            err_str = str(e)
            if not err_str:
                err_str = type(e).__name__
            if self.proxy and ("proxy" in err_str.lower() or "connect" in err_str.lower()):
                self.proxy_failed = True
            return {"success": False, "error": err_str}
    def update_account_sync(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        max_retries = 2
        last_error = None
        for attempt in range(max_retries):
            try:
                future = asyncio.run_coroutine_threadsafe(
                    self.update_account_with_live_session(payload), _async_loop
                )
                result = future.result()
                if result["success"]:
                    return result
                error = str(result.get("error", ""))
                if self._is_transient_error(error):
                    last_error = self._clean_error(error)
                    if proxy_manager and attempt < max_retries - 1:
                        new_proxy = proxy_manager.get_proxy()
                        if new_proxy:
                            self.proxy = new_proxy
                            self.client = primp.Client(verify=False, proxy=parse_proxy(new_proxy))
                        continue
                return result
            except Exception as e:
                last_error = self._clean_error(str(e))
                if attempt < max_retries - 1 and proxy_manager:
                    new_proxy = proxy_manager.get_proxy()
                    if new_proxy:
                        self.proxy = new_proxy
                        self.client = primp.Client(verify=False, proxy=parse_proxy(new_proxy))
                    continue
        return {"success": False, "error": last_error or "Max retries reached"}
    def _clean_error(self, error) -> str:
        error = str(error)
        if "RATE_LIMIT" in error or "rate limit" in error.lower() or "too often" in error.lower():
            return "Rate Limited"
        if "curl:" in error:
            if "(56)" in error:
                return "Proxy closed"
            elif "(28)" in error:
                return "Timeout"
            elif "(7)" in error:
                return "Proxy failed"
            else:
                match = re.search(r'curl: \((\d+)\)', error)
                if match:
                    return f"Curl {match.group(1)}"
        if "Unknown Session" in error:
            return "Bad session"
        if "received 4000" in error or "4000 (private" in error:
            return "Token locked / flagged (WS 4000)"
        if "received 4001" in error:
            return "Invalid token (WS 4001)"
        if "received 4004" in error:
            return "Auth failed (WS 4004)"
        if "received 4006" in error:
            return "Session invalid (WS 4006)"
        if "Unauthorized" in error or "401" in error:
            return "Unauthorized"
        if "captcha" in error.lower():
            return "Captcha"
        if "Invalid Form Body" in error:
            return "Invalid request"
        if "message" in error and "code" in error:
            match = re.search(r"'message': '([^']+)'", error)
            if match:
                msg = match.group(1)
                if len(msg) > 25:
                    return msg[:22] + "..."
                return msg
        if len(error) > 80:
            return error[:77] + "..."
        return error
    def get_headers(self) -> Dict[str, str]:
        headers = {
            "accept": "*/*",
            "accept-encoding": "gzip, deflate, br",
            "accept-language": "en-US",
            "authorization": self.token,
            "content-type": "application/json",
            "user-agent": self.user_agent,
            "x-debug-options": "bugReporterEnabled",
            "x-discord-locale": "en-US",
            "x-discord-timezone": "Asia/Calcutta",
            "x-installation-id": self.installation_id,
            "x-super-properties": self._super_props
        }
        fp = self.get_fingerprint()
        if fp:
            headers["x-fingerprint"] = fp
        return headers
    def _is_transient_error(self, error_str: str) -> bool:
        lower = error_str.lower()
        return any(kw in lower for kw in (
            "connection", "proxy", "timeout", "reset", "connect",
            "sending", "refused", "unreachable", "eof", "read error",
            "gateway ready", "gateway identify", "gateway",
            "no close frame", "connection closed", "websocket"
        ))
    def _api_call_with_retry(self, method: str, url: str, data: Dict[str, Any],
                              headers: Dict[str, str], max_retries: int = 5) -> Dict[str, Any]:
        if getattr(self, "is_locked", False):
            return {"success": False, "error": "Token Locked"}
        last_result = None
        for attempt in range(max_retries):
            if getattr(self, "is_locked", False):
                return {"success": False, "error": "Token Locked"}
            try:
                if method.upper() == "POST":
                    resp = self.client.post(url, headers=headers, json=data, timeout=60)
                else:
                    resp = self.client.patch(url, headers=headers, json=data, timeout=60)
                if resp.status_code in (200, 204):
                    try:
                        data = resp.json() if resp.text and resp.status_code == 200 else {}
                    except Exception:
                        data = {}
                    return {"success": True, "data": data}
                try:
                    error_data = resp.json() if resp.text and resp.text.strip() else {}
                except Exception:
                    error_data = {}
                if error_data.get("captcha_key"):
                    return {"success": False, "captcha": True, "error": error_data}
                if resp.status_code == 400 and isinstance(error_data, dict):
                    code = error_data.get("code")
                    if code == 10020:
                        return {"success": False, "unknown_session": True, "error": "Unknown Session"}
                    errors = error_data.get("errors", {})
                    for field_errors in errors.values():
                        for err in field_errors.get("_errors", []):
                            if err.get("code") == "AVATAR_RATE_LIMIT":
                                return {"success": False, "rate_limited": True, "retry_after": 0, "error": "Avatar Rate Limited"}
                if resp.status_code == 429:
                    try:
                        ra_header = resp.headers.get("retry-after") or resp.headers.get("Retry-After")
                        ra_body = error_data.get("retry_after", 0) if isinstance(error_data, dict) else 0
                        retry_after = float(ra_header) if ra_header else float(ra_body or 0)
                    except (TypeError, ValueError):
                        retry_after = 0
                    wait_time = max(retry_after, 1.0)
                    time.sleep(wait_time)
                    continue  
                last_result = {"success": False, "error": error_data}
                if resp.status_code in (401, 403):
                    self.is_locked = True
                    return last_result
            except Exception as e:
                error_str = str(e)
                last_result = {"success": False, "error": error_str}
                if self.proxy and self._is_transient_error(error_str):
                    self.proxy_failed = True
                if self._is_transient_error(error_str) and proxy_manager and attempt < max_retries - 1:
                    new_proxy = proxy_manager.get_proxy()
                    if new_proxy:
                        self.proxy = new_proxy
                        self.client = primp.Client(verify=False, proxy=parse_proxy(new_proxy))
                    continue
                if attempt >= max_retries - 1:
                    return last_result
        return last_result or {"success": False, "error": "Max retries reached"}
    def update_user_profile(self, data: Dict[str, Any], headers: Dict[str, str]) -> Dict[str, Any]:
        return self._api_call_with_retry("patch", f"{DISCORD_API}/users/@me", data, headers)
    def update_profile_fields(self, data: Dict[str, Any], headers: Dict[str, str]) -> Dict[str, Any]:
        return self._api_call_with_retry("patch", f"{DISCORD_API}/users/@me/profile", data, headers)
    def set_hypesquad(self, house_id: int, headers: Dict[str, str], retry_count: int = 0) -> Dict[str, Any]:
        time.sleep(random.uniform(2, 5))
        house_name = HYPESQUAD_HOUSES.get(house_id, "Unknown")
        try:
            check = self.client.get(
                f"{DISCORD_API}/users/@me",
                headers=headers,
                timeout=30
            )
            if check.status_code == 200:
                data = check.json()
                flags = data.get("flags", 0)
                if flags & 0xE:
                    existing_house = None
                    for hid, hname in HYPESQUAD_HOUSES.items():
                        if flags & (1 << hid):
                            existing_house = hname
                            break
                    if existing_house:
                        log("INFO", self.token, f"[HypeSquad Already Set : {existing_house}]")
                        return {"success": True, "house_name": existing_house, "already_set": True}
        except Exception:
            pass
        res = self._api_call_with_retry(
            "post",
            f"{DISCORD_API}/hypesquad/online",
            {"house_id": house_id},
            headers,
            max_retries=2
        )
        if res.get("success"):
            return {"success": True, "house_name": house_name}
        if retry_count < RETRY_LIMIT:
            log("WARN", self.token, f"[HypeSquad Retry : {retry_count + 1}/{RETRY_LIMIT} for {house_name}]")
            time.sleep(random.uniform(2.0, 4.0))
            return self.set_hypesquad(house_id, headers, retry_count + 1)
        return {"success": False, "error": f"HypeSquad {house_name} not applied - Account may already have a badge or is rate limited", "house_name": house_name}
    def process(self, names: List[str], bios: List[str], pronouns_list: List[str],
                avatar_files: List[Path], avatar_loader) -> bool:
        headers = self.get_headers()
        success = True
        parallel_tasks = []
        account_payload = {}
        avatar_name = None
        if UPDATE_AVATAR and avatar_files:
            avatar_path = random.choice(avatar_files)
            avatar_b64 = avatar_loader(avatar_path)
            if avatar_b64:
                account_payload["avatar"] = avatar_b64
                av_hash = hashlib.md5(avatar_b64[:100].encode()).hexdigest()
                now = datetime.now()
                now_str = now.strftime("%B {d}, %Y at {t}").format(
                    d=now.day,
                    t=now.strftime("%I:%M %p").lstrip("0")
                )
                account_payload["avatar_description"] = f"{av_hash}, added {now_str}"
                avatar_name = avatar_path.name
        display_name = None
        if UPDATE_DISPLAY_NAME and names:
            display_name = random.choice(names)
            account_payload["global_name"] = display_name
        if account_payload:
            parallel_tasks.append(("account", (account_payload, avatar_name, display_name)))
        profile_payload = {}
        bio = None
        if UPDATE_BIO and bios:
            bio = random.choice(bios)
            profile_payload["bio"] = bio
        pronouns = None
        if UPDATE_PRONOUNS and pronouns_list:
            pronouns = random.choice(pronouns_list)
            profile_payload["pronouns"] = pronouns
        if profile_payload:
            parallel_tasks.append(("profile", (profile_payload, bio, pronouns)))
        house_id = None
        house_name = None
        if UPDATE_HYPESQUAD:
            time.sleep(random.uniform(0, 3))
            house_id = random.choice([1, 2, 3])
            house_name = HYPESQUAD_HOUSES[house_id]
            parallel_tasks.append(("hypesquad", (house_id, house_name)))
        if parallel_tasks:
            def _run_field(task_type, value):
                if getattr(self, "is_locked", False):
                    return (task_type, {"success": False, "error": "Token Locked"}, value)
                h = headers.copy()
                if task_type == "account":
                    payload, _, _ = value
                    if "avatar" in payload:
                        return ("account", self.update_account_sync(payload), value)
                    else:
                        return ("account", self.update_user_profile(payload, h), value)
                elif task_type == "profile":
                    payload, _, _ = value
                    return ("profile", self.update_profile_fields(payload, h), value)
                elif task_type == "hypesquad":
                    hid, _ = value
                    return ("hypesquad", self.set_hypesquad(hid, h), value)
                return ("unknown", {"success": False, "error": "Unknown field type"}, value)
            with ThreadPoolExecutor(max_workers=len(parallel_tasks)) as field_executor:
                futures = [field_executor.submit(_run_field, tt, val) for tt, val in parallel_tasks]
                for future in as_completed(futures):
                    try:
                        task_type, result, values = future.result()
                    except Exception as e:
                        log("FAILED", self.token, f"[Field Error : {str(e)[:30]}]")
                        success = False
                        continue
                    if task_type == "account":
                        _, aname, dname = values
                        if result["success"]:
                            pass
                        elif result.get("captcha"):
                            if aname: log("WARN", self.token, "[Avatar Failed : Captcha]")
                            if dname: log("WARN", self.token, "[Name Failed : Captcha]")
                            success = False
                        elif result.get("rate_limited"):
                            ra = result.get("retry_after", 0)
                            ra_str = f"{int(ra)}s" if ra else "unknown"
                            if aname: log("WARN", self.token, f"[Avatar Failed : Rate Limited ({ra_str})]")
                            if dname: log("WARN", self.token, f"[Name Failed : Rate Limited ({ra_str})]")
                            success = False
                        else:
                            error_msg = self._clean_error(result.get("error", "Unknown"))
                            if aname: log("FAILED", self.token, f"[Avatar Failed : {error_msg}]")
                            if dname: log("FAILED", self.token, f"[Name Failed : {error_msg}]")
                            success = False
                    elif task_type == "profile":
                        _, bname, pname = values
                        if result["success"]:
                            pass
                        elif result.get("captcha"):
                            if bname: log("WARN", self.token, "[Bio Failed : Captcha]")
                            if pname: log("WARN", self.token, "[Pronouns Failed : Captcha]")
                            success = False
                        else:
                            error_msg = self._clean_error(result.get("error", "Unknown"))
                            if bname: log("FAILED", self.token, f"[Bio Failed : {error_msg}]")
                            if pname: log("FAILED", self.token, f"[Pronouns Failed : {error_msg}]")
                            success = False
                    elif task_type == "hypesquad":
                        _, hsname = values
                        if result.get("success"):
                            applied_house = result.get("house_name", hsname)
                        else:
                            error_msg = self._clean_error(result.get("error", "Unknown"))
                            log("FAILED", self.token, f"[HypeSquad Failed : {hsname} - {error_msg}]")
                            success = False
        if self.proxy_failed and proxy_manager:
            proxy_manager.mark_bad(self.proxy)
        return success
def process_token(token: str, names: List[str], bios: List[str], pronouns_list: List[str],
                  avatar_files: List[Path], avatar_loader) -> bool:
    proxy = proxy_manager.get_proxy() if proxy_manager else None
    humanizer = Humanizer(token, proxy)
    try:
        return humanizer.process(names, bios, pronouns_list, avatar_files, avatar_loader)
    finally:
        if proxy_manager and proxy:
            proxy_manager.release_proxy(proxy)
def stats_updater():
    while True:
        time.sleep(2)
        with stats_lock:
            total = stats['total']
            gen = stats['generated']
            ver = stats['verified']
            cap_fail = stats['captcha_failed']
            cap_solved = stats['captcha_solved']
            locked = stats['locked']
            valid = stats['valid']
        gen_pct = (gen / total * 100) if total else 0
        ver_pct = (ver / total * 100) if total else 0
        cap_fail_pct = (cap_fail / total * 100) if total else 0
        cap_solved_pct = (cap_solved / total * 100) if total else 0
        locked_pct = (locked / total * 100) if total else 0
        valid_pct = (valid / total * 100) if total else 0
        current_time = datetime.now().strftime('%H:%M')
        title = f"APZX | Gen: {gen} | EV: {ver} | Cap: {cap_solved}/{cap_fail} | Locked: {locked} | Invalid: {valid} | Total: {total}"
        try:
            import ctypes
            ctypes.windll.kernel32.SetConsoleTitleW(title)
        except Exception:
            pass
        import os
        if os.environ.get("GUI_MODE") == "1":
            print(f"GUI_STAT:{gen},{ver},{cap_solved},{cap_fail},{locked},{valid},{total}")
def display_banner():
    import os
    import sys
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    if os.environ.get("GUI_MODE") == "1":
        return
    if os.name == "nt":
        os.system("")
    os.system("cls" if os.name == "nt" else "clear")
    print(f"""{P}              :::     ::::::::: ::::::::: :::    :::          ::::::::   ::::::::  ::::    :::
       :+: :+:   :+:    :+:     :+:  :+:    :+:         :+:    :+: :+:    :+: :+:+:   :+:
     +:+   +:+  +:+    +:+    +:+    +:+  +:+          +:+               +:+ :+:+:+  +:+
   +#++:++#++: +#++:++#+    +#+      +#++:+           :#:            +#++:  +#+ +:+ +#+
  +#+     +#+ +#+         +#+      +#+  +#+          +#+   +#+#        +#+ +#+  +#+#+#
 #+#     #+# #+#        #+#      #+#    #+#         #+#    #+# #+#    #+# #+#   #+#+#
###     ### ###       ######### ###    ###          ########   ########  ###    ####
""")
if __name__ == "__main__":
    display_banner()
    cap_cfg = config.get("9captcha", {})
    api_key = cap_cfg.get("api_key", "").strip()
    if not api_key:
        print(f"  {Fore.RED}⚠ No 9Captcha API key set!{Style.RESET_ALL}")
        print(f"  {Fore.YELLOW}  Get your key at: https://9captcha.pridesmp.fun{Style.RESET_ALL}")
        print(f"  {Fore.YELLOW}  Set it in config.json under 9captcha.api_key or via Settings menu.{Style.RESET_ALL}")
        sys.exit(1)
    ext_mode = cap_cfg.get("extension_solver", True)
    vps_mode = cap_cfg.get("req_solver", False)
    mode_str = []
    if ext_mode: mode_str.append("Extension")
    if vps_mode: mode_str.append("Request")
    print(f"  {D}│{R} {D}Solver:{R} {G}{' + '.join(mode_str) if mode_str else 'None!'}{R}")
    if ext_mode:
        try:
            from engine.extension_browser import get_browser, sync_api_key
            print(f"  {D}│{R} {C}Validating 9Captcha API Key...{R}")
            api_key_valid = sync_api_key()
            if api_key_valid == "SERVER_ERROR":
                print(f"  {D}│{R} {Fore.YELLOW}⚠ Server error! The captcha API might be down. Please check again in 3-4 minutes.{R}")
                sys.exit(1)
            elif not api_key_valid:
                print(f"  {D}│{R} {Fore.RED}⚠ FATAL: Invalid 9Captcha API Key. Generator explicitly aborted!{R}")
                sys.exit(1)
            print(f"  {D}│{R} {C}Initializing extension browser...{R}")
            print(f"  {D}│{R} {G}✓ Extension browser ready{R}")
        except SystemExit:
            raise
        except ImportError as e:
            print(f"  {D}│{R} {Fore.YELLOW}⚠ Extension browser unavailable: {e}{R}")
            print(f"  {D}│{R} {D}  pip install truedriver{R}")
            
        import atexit
        def cleanup_browser():
            try: get_browser().stop()
            except: pass
        atexit.register(cleanup_browser)

    if vps_mode:
        p_path = Path("input/proxies.txt")
        has_proxies = p_path.exists() and len(open(p_path).readlines()) > 0
        if not has_proxies:
            print(f"  {D}│{R} {Fore.RED}⚠ FATAL: Request solver does NOT work without proxies!{R}")
            print(f"  {D}│{R} {Fore.RED}  Our servers use datacenter IPs which Discord blocks.{R}")
            print(f"  {D}│{R} {Fore.YELLOW}  Please add quality residential proxies to input/proxies.txt{R}")
            print(f"  {D}│{R} {Fore.YELLOW}  Or switch to Extension solver in Settings >Extension solver.{R}")
            sys.exit(1)
            
    print()
    print()
    
    warp_enabled = config.get("cloudflare_warp", {}).get("enabled", False)
    NUM_THREADS = int(config.get("threading", {}).get("generator", config.get("threads", 1)))
    
    if warp_enabled and vps_mode:
        print(f"  {D}│{R} {Fore.YELLOW}⚠ Cloudflare Warp Rotation disabled because Request Solver is ON.{R}")
        warp_enabled = False

    if warp_enabled:
        try:
            warp_cli_path = r"C:\Program Files\Cloudflare\Cloudflare WARP\warp-cli.exe"
            subprocess.run([warp_cli_path, "--version"], capture_output=True, check=True)
        except (FileNotFoundError, subprocess.CalledProcessError):
            print(f"  {D}│{R} {Fore.RED}⚠ FATAL: Cloudflare Warp Rotation is ENABLED but warp-cli is not installed!{R}")
            print(f"  {D}│{R} {Fore.RED}  Please install Cloudflare Warp or disable rotation in Settings.{R}")
            sys.exit(1)

        print(f"  {D}│{R} {Fore.YELLOW}⚠ Cloudflare Warp Rotation ENABLED{R}")
        print(f"  {D}│{R} {Fore.YELLOW}  Forcing Generator Threads to 1 to prevent socket drops.{R}")
        print(f"  {D}│{R} {Fore.YELLOW}  Proxies will be ignored.{R}")
        NUM_THREADS = 1

    def rotate_warp_ip():
        print(f"  {D}│{R} {Fore.CYAN}↻ Rotating Cloudflare Warp IP...{Style.RESET_ALL}")
        try:
            warp_cli_path = r"C:\Program Files\Cloudflare\Cloudflare WARP\warp-cli.exe"
            subprocess.run([warp_cli_path, "disconnect"], capture_output=True)
            time.sleep(1.5)
            subprocess.run([warp_cli_path, "connect"], capture_output=True)
            time.sleep(1.0)
            
            # Wait for internet connectivity to restore before continuing
            new_ip = None
            for _ in range(15):
                try:
                    new_ip = requests.get("https://api.ipify.org", timeout=3).text.strip()
                    break
                except Exception:
                    time.sleep(1)
                    
            if new_ip:
                print(f"  {D}│{R} {Fore.GREEN}✓ Warp IP Rotated to: {new_ip}{Style.RESET_ALL}")
            else:
                print(f"  {D}│{R} {Fore.YELLOW}⚠ Warp IP Rotated (Network is slow/unstable){Style.RESET_ALL}")
        except FileNotFoundError:
            print(f"  {D}│{R} {Fore.RED}⚠ warp-cli not found. Is Cloudflare Warp installed?{Style.RESET_ALL}")
        except Exception as e:
            print(f"  {D}│{R} {Fore.RED}⚠ Warp rotation failed: {e}{Style.RESET_ALL}")

    semaphore = threading.Semaphore(NUM_THREADS)
    _stop_event = threading.Event()
    _clear_debug_log()
    def _signal_handler(sig, frame):
        if not _stop_event.is_set():
            _stop_event.set()
            print(f"\n  {Fore.YELLOW}⚠ Halting generator immediately...{R}")
            os._exit(0)
    import signal
    try:
        signal.signal(signal.SIGINT, _signal_handler)
    except Exception:
        pass

    if os.environ.get("GUI_MODE") != "1":
        try:
            import keyboard
            keyboard.add_hotkey('ctrl+x', lambda: _signal_handler(None, None))
        except Exception:
            pass
            
    stats_thread = threading.Thread(target=stats_updater, daemon=True)
    stats_thread.start()
    def worker(current_num):
        use_local_ip = config.get("use_local_ip", False)
        if use_local_ip:
            proxy = None
            Log.status(f"[Local IP] Account #{current_num} — no proxy, 90s cooldown between accounts")
        else:
            proxy = proxy_manager.pop_top() if proxy_manager and not warp_enabled else None
            if proxy is None:
                use_local_ip = True
                Log.status(f"[Auto-Fallback] No proxies available — switching to Local IP mode (90s cooldown)")
        mail_api_temp, mail_provider_name_temp = get_mail_provider()
        if not mail_api_temp:
            mail_api_temp = APZMailApi(logger=print)
        email = mail_api_temp.create_account(proxy=proxy)
        if use_local_ip:
            time.sleep(90)
        if not email:
            if isinstance(mail_api_temp, ZeusProvider):
                reason = getattr(mail_api_temp, '_last_error', '') or 'unknown_error'
                bal = mail_api_temp.check_balance()
                try:
                    no_bal = bal is not None and float(bal) <= 0
                except (ValueError, TypeError):
                    no_bal = False
                    
                if no_bal:
                    Log.error(f"No Balance (Zeus: {bal})")
                else:
                    reason_lower = str(reason).lower()
                    if "stock" in reason_lower or "quantity" in reason_lower or "enough" in reason_lower or "empty" in reason_lower:
                        Log.error(f"No Stock ({reason}) — waiting 30s...")
                        time.sleep(30)
                        # Retry after waiting
                        email = mail_api_temp.create_account(proxy=proxy)
                        if not email:
                            new_reason = getattr(mail_api_temp, '_last_error', '') or reason
                            Log.error(f"Still No Stock ({new_reason}) — skipping")
                            if proxy: proxy_manager.release_proxy(proxy)
                            semaphore.release()
                            return
                    else:
                        Log.error(f"Zeus Failed: {reason} (Bal: {bal})")
                        if proxy: proxy_manager.release_proxy(proxy)
                        semaphore.release()
                        return
            else:
                Log.error("emails are not available")
                if proxy: proxy_manager.release_proxy(proxy)
                semaphore.release()
                return
        if not email:
            if proxy: proxy_manager.release_proxy(proxy)
            semaphore.release()
            return
        username = _random_username()
        mail_pass = None
        if hasattr(mail_api_temp, '_email_data') and isinstance(mail_api_temp._email_data, dict):
            mail_pass = mail_api_temp._email_data.get("password")
        elif hasattr(mail_api_temp, 'password') and mail_api_temp.password:
            mail_pass = mail_api_temp.password
        password = mail_pass if mail_pass else _random_password()
        try:
            generate_apzx_token(email, username, password, proxy, current_num, mail_api_temp, mail_provider_name_temp, use_local_ip)
        finally:
            if proxy:
                proxy_manager.release_proxy(proxy)
            semaphore.release()
    while not _stop_event.is_set():
        semaphore.acquire()
        if _stop_event.is_set():
            semaphore.release()
            break
        
        if warp_enabled:
            rotate_warp_ip()
            
        with gen_lock:
            gen_count += 1
            current_num = gen_count
        t = threading.Thread(target=worker, args=(current_num,), daemon=True)
        t.start()
    print(f"  {G}✓ Generator stopped cleanly.{R}")
