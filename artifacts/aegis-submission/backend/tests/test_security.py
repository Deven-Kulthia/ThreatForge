"""Security-boundary and competition-compliance tests.

These encode the competition's hard constraints as executable checks, so a violation
fails the build rather than surviving into a submission:

  Rules §3(a) — synthetic data only; no real cardholder data, PII or production data
  Rules §3(b) — adversarial testing must not target live systems or third parties
  Kaggle Foundational §6c — dependencies must be OSI-permissive
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pandas as pd
import pytest

from backend.app import attacks as A
from backend.app import generator as G

APP = Path(__file__).resolve().parents[1] / "app"
ROOT = Path(__file__).resolve().parents[2]

# Modules that constitute the attack simulator. These in particular must have no way to
# reach anything outside this process.
SIMULATOR_MODULES = ["attacks.py", "generator.py", "schema.py", "features.py"]

NETWORK_MODULES = {
    "socket", "ssl", "http", "http.client", "urllib", "urllib.request", "ftplib",
    "telnetlib", "smtplib", "requests", "httpx", "aiohttp", "urllib3", "websocket",
    "websockets", "paramiko", "pycurl", "boto3", "selenium",
}

DANGEROUS_CALLS = {"eval", "exec", "compile", "__import__"}


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text())
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module)
    return found


# --------------------------------------------------------------------------------------
# Rules §3(b) — the simulator cannot target a live system
# --------------------------------------------------------------------------------------


@pytest.mark.parametrize("module", SIMULATOR_MODULES)
def test_simulator_has_no_network_capability(module):
    """Network isolation is enforced structurally: the code cannot open a connection."""
    imported = _imports(APP / module)
    offenders = {i for i in imported if i.split(".")[0] in NETWORK_MODULES}
    assert not offenders, f"{module} imports network capability: {offenders}"


@pytest.mark.parametrize("module", SIMULATOR_MODULES)
def test_simulator_has_no_subprocess_or_dynamic_execution(module):
    imported = _imports(APP / module)
    assert "subprocess" not in imported
    assert "os" not in imported or module == "schema.py"

    tree = ast.parse((APP / module).read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id not in DANGEROUS_CALLS, \
                f"{module} calls {node.func.id}()"


def test_no_hardcoded_urls_in_simulator():
    """No external endpoint should be referenced anywhere in the attack path."""
    url = re.compile(r"https?://(?!localhost|127\.0\.0\.1)", re.IGNORECASE)
    for module in SIMULATOR_MODULES:
        text = (APP / module).read_text()
        # Documentation references (arXiv, standards bodies) live in research/, not code.
        assert not url.search(text), f"{module} contains an external URL"


# --------------------------------------------------------------------------------------
# Rules §3(a) — synthetic data only
# --------------------------------------------------------------------------------------


@pytest.fixture(scope="module")
def sample():
    pop = G.build_population(n_cardholders=120, n_merchants=40, seed=1)
    hist = G.generate_legit(pop, days=8, seed=2)
    camps = A.run_all(pop, hist, strength=0.7, seed=4)
    return pd.concat([hist] + [c.transactions for c in camps], ignore_index=True)


def test_every_record_is_flagged_synthetic(sample):
    assert sample["synthetic"].all()


def test_no_card_identifier_resembles_a_pan(sample):
    """Card identifiers are synthetic tokens. A 13-19 digit run would look like a PAN."""
    pan = re.compile(r"\d{13,19}")
    assert not sample["card_token"].astype(str).str.contains(pan).any()
    assert not sample["account_id"].astype(str).str.contains(pan).any()
    assert sample["card_token"].astype(str).str.startswith("tok_").all()


def test_no_luhn_valid_numbers_in_card_identifiers(sample):
    """Belt and braces: even a coincidental Luhn-valid digit string in a CARD identifier
    is unacceptable, because that is the field a reviewer would scrutinise for PANs.

    `transaction_id` is deliberately excluded: it is an internal reference of the form
    `<attack>_<uid>_<counter>`, whose digit run can pass Luhn by coincidence without
    resembling a card number in any meaningful sense.
    """
    def luhn(s: str) -> bool:
        ds = [int(c) for c in s if c.isdigit()]
        if len(ds) < 13:
            return False
        checksum, parity = 0, len(ds) % 2
        for i, d in enumerate(ds):
            if i % 2 == parity:
                d *= 2
                if d > 9:
                    d -= 9
            checksum += d
        return checksum % 10 == 0

    for col in ("card_token", "account_id"):
        offenders = [v for v in sample[col].astype(str).unique() if luhn(v)]
        assert not offenders, f"{col} contains Luhn-valid values: {offenders[:3]}"


def test_card_identifiers_carry_short_digit_runs(sample):
    """A card token must not contain a digit run long enough to be mistaken for a PAN."""
    run = re.compile(r"\d{13,}")
    for col in ("card_token", "account_id"):
        assert not sample[col].astype(str).str.contains(run).any()


def test_no_personal_names_or_contact_details(sample):
    """The schema carries no PII fields at all — verify none crept in."""
    banned = {"name", "email", "phone", "address", "dob", "ssn", "national_id",
              "first_name", "last_name", "postcode", "zip"}
    cols = {c.lower() for c in sample.columns}
    # merchant_name is a business descriptor, not personal data.
    assert not (cols & banned) - {"merchant_name"}
    assert not sample["merchant_name"].astype(str).str.contains("@").any()


def test_ip_prefixes_are_truncated(sample):
    """Only /24 prefixes are retained — never a full address."""
    assert sample["ip_prefix"].astype(str).str.endswith("/24").all()


def test_synthetic_flag_cannot_be_disabled():
    """There must be no code path that emits a record marked non-synthetic."""
    for module in ("generator.py", "attacks.py"):
        text = (APP / module).read_text()
        assert '"synthetic": False' not in text
        assert "synthetic=False" not in text


# --------------------------------------------------------------------------------------
# Secrets hygiene — the repository must contain none
# --------------------------------------------------------------------------------------


def test_no_secrets_committed_in_source():
    patterns = [
        re.compile(r"ghp_[A-Za-z0-9]{20,}"),          # GitHub PAT
        re.compile(r"sk-[A-Za-z0-9]{20,}"),           # generic API key
        re.compile(r"AKIA[0-9A-Z]{16}"),              # AWS access key
        re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY"),
    ]
    for path in list(APP.glob("*.py")) + list((ROOT / "scripts").glob("*.py")):
        text = path.read_text()
        for p in patterns:
            assert not p.search(text), f"possible secret in {path.name}"


def test_env_example_contains_only_placeholders():
    text = (ROOT / ".env.example").read_text()
    assert "ghp_" not in text
    assert re.search(r"GITHUB_TOKEN=\s*(<[^>]+>)?\s*$", text, re.MULTILINE)


def test_gitignore_excludes_env():
    ignored = (ROOT / ".gitignore").read_text()
    assert re.search(r"^\.env$", ignored, re.MULTILINE)
    assert ".env.*" in ignored


# --------------------------------------------------------------------------------------
# Kaggle Foundational §6c — permissive dependencies only
# --------------------------------------------------------------------------------------


def test_dependencies_are_permissively_licensed():
    """No copyleft dependency may enter the runtime requirements."""
    reqs = (ROOT / "requirements.txt").read_text().lower()
    for banned in ("agpl", "gpl", "sdv", "ctgan", "copyleft"):
        assert banned not in reqs, f"requirements.txt references {banned}"


def test_no_operational_fraud_instructions_in_taxonomy():
    """Attacks are described as observable behaviour, never as how-to guidance."""
    forbidden = re.compile(
        r"\b(step 1|how to obtain|purchase (?:stolen|dumps)|carding forum|"
        r"bypass the following|use this script to)\b", re.IGNORECASE)
    for spec in A.TAXONOMY.values():
        blob = f"{spec.description} {spec.genai_role}"
        assert not forbidden.search(blob), f"{spec.id} reads as operational guidance"
