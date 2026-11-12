# جمعية الفرقان لتعليم القرآن – القسم الابتدائي | متابعة الطلبة (Streamlit)
import csv
import hashlib
import calendar
import io
import os
import random
import re
import time
import uuid
import urllib.parse
import zipfile
import datetime as dt
from zoneinfo import ZoneInfo

import streamlit as st

def _section_cfg():
    """إعدادات القسم من Secrets ([section]) لتشغيل نسخة ثانية من التطبيق لقسم آخر. بدونها تبقى إعدادات القسم الابتدائي."""
    try:
        return dict(st.secrets["section"])
    except Exception:
        return {}


def _all_sections():
    """وضع الأقسام المتعددة: Secrets فيها [sections.<مفتاح>] لكل قسم. بدونها يعمل التطبيق لقسم واحد."""
    try:
        return {str(k): dict(v) for k, v in dict(st.secrets["sections"]).items()}
    except Exception:
        return {}


def _default_key():
    try:
        return str(st.secrets["general"]["default_section"])
    except Exception:
        return ""


SECS = _all_sections()
MULTI = bool(SECS)
SECKEY = ""
GENERIC = False  # وضع الأقسام المتعددة قبل معرفة القسم (صفحة الدخول أو اختيار الأولياء للقسم)
if MULTI:
    _q = st.query_params
    if _q.get("v") == "p":
        SECKEY = _q.get("s") if _q.get("s") in SECS else (_default_key() if _default_key() in SECS else "")
    else:
        SECKEY = st.session_state.get("sec_key", "") if st.session_state.get("sec_key", "") in SECS else ""
    GENERIC = not SECKEY
    _SC = SECS[SECKEY] if SECKEY else {"name": "منصة متابعة الطلبة", "director": "—", "sheikh1": "—", "sheikh2": "—", "user0": "_u0", "user1": "_u1", "user2": "_u2"}
else:
    _SC = _section_cfg()
SEC = _SC.get("name", "القسم الابتدائي")  # اسم القسم
ASSOC = _SC.get("assoc", "جمعية الفرقان لتعليم القرآن")
CITY = _SC.get("city", "دار البيضاء")
DIR_N = _SC.get("director", "الشيخ أسامة")  # مدير القسم وشيخ الحفظ
REV1_N = _SC.get("sheikh1", "الشيخ هارون")
REV2_N = _SC.get("sheikh2", "الشيخ حذيفة")
U0, U1, U2 = _SC.get("user0", "osama"), _SC.get("user1", "haroun"), _SC.get("user2", "houdhayfa")
SEEDED = (str(_SC.get("seeded", "")).strip() in ("1", "true", "yes")) if MULTI else not _SC  # قوائم الأسماء الأولية خاصة بالقسم الابتدائي
SOLO = str(_SC.get("solo", "")).strip() in ("1", "true", "yes")  # شيخ واحد يجمع الحفظ والمراجعة (لا شيوخ مراجعة آخرون)
if SOLO:
    U1 = U2 = U0


def app_link():
    """رابط صفحة الأولياء (في الأقسام المتعددة يحمل مفتاح القسم)."""
    try:
        base = str(st.secrets["app_url"]).rstrip("/")
    except Exception:
        base = ""
    return base + "/?v=p" + (f"&s={SECKEY}" if MULTI else "")


def short_n(n):
    return n.replace("الشيخ ", "", 1)


st.set_page_config(page_title=f"{ASSOC.replace(' لتعليم القرآن', '')} – {SEC}", page_icon="📖", layout="centered")

# ───────────────────────── الإعدادات ─────────────────────────
TZ = ZoneInfo("Africa/Algiers")
HERE = os.path.dirname(os.path.abspath(__file__))

HEAD = {
    "students": ["id", "name", "grp", "pin", "days", "exempt", "mdays", "target", "ptarget", "pstatus", "psur"],
    "logs": ["id", "sid", "date", "teacher", "role", "type", "detail", "grade", "note", "ts", "qty", "sur", "a1", "a2", "kind", "sur2", "err"],
    "disc": ["id", "sid", "date", "teacher", "score"],
    "audit": ["id", "ts", "who", "act", "detail"],
    "ann": ["id", "date", "text", "until", "by"],
    "cfg": ["id", "key", "val"],
    "msg": ["id", "sid", "who", "to", "ts", "text", "read"],
    "visits": ["id", "sid", "ts"],
    "chat": ["id", "ts", "who", "to", "text", "kind"],
    "exams": ["id", "sid", "date", "kind", "part", "score", "note", "teacher"],
    "att": ["id", "sid", "date", "status", "teacher", "why", "by"],
    "pre": ["id", "sid", "date", "why", "ts"],
    "pay": ["id", "sid", "month", "amount", "date", "teacher"],
    "sug": ["id", "ts", "sec", "who", "text", "status", "reply"],
}

TEACHERS = [
    {"n": DIR_N, "r": "حفظ", "t": "hifz", "u": U0, "admin": True},
    {"n": REV1_N, "r": "مراجعة 1", "t": "mur", "u": U1},
    {"n": REV2_N, "r": "مراجعة 2", "t": "mur", "u": U2},
]
if SOLO:  # حساب واحد بدورين: الحفظ والمراجعة، يبدّل بينهما من أعلى الصفحة
    TEACHERS = [TEACHERS[0], {"n": DIR_N, "r": "مراجعة", "t": "mur", "u": U0, "admin": True, "alias": True}]
STAFF = [t for t in TEACHERS if not t.get("alias")]
# بصمات الرموز السرية (SHA-256). يمكن تغييرها من Secrets دون لمس الكود: [staff] osama="..."
_OSAMA_HASHES = {
    "osama": "8d21a129d727d17ab7f7c08bcd3ec5751b636b281dbdb8d453a66a41eb8ef1b4",
    "haroun": "5f83a1a0fbbffbed5626ecb428010ce8edb203aeaf4d02ac3fe930914001e2fc",
    "houdhayfa": "f740c467927dd4af113e04370b11d4217ccfefb896a9fae8de43a5b669eb58f3",
}
DEFAULT_HASHES = _OSAMA_HASHES if SEEDED else {}
WEEK_START = 5  # بداية الأسبوع: السبت (الاثنين=0 ... السبت=5 ... الأحد=6)
GRADES = ["ممتاز", "جيد جدا", "جيد", "متوسط", "يحتاج إعادة"]
GRADES_H = GRADES + ["لم يحفظ"]  # «لم يحفظ»: لا مقدار جديد في تلك الحلقة
HK = {"new": "حفظ جديد (مقطع جديد)", "rep": "تكرار (تجميع السورة بعد تقسيمها)", "old": "إعادة قديمة"}  # يُحتسب الجديد وحده في التقدم
DAYS = {"sat": ("السبت", 5), "sun": ("الأحد", 6), "tue": ("الثلاثاء", 1), "wed": ("الأربعاء", 2)}  # أيام الحفظ مع شيخ الحفظ (weekday: الاثنين=0)
SUN_NAMES = [] if not SEEDED else ["بن بثرة ياسر", "مبدوعة عبد الرحيم", "ربحاوي عبد الرؤوف", "حجاب ادريس", "قبلي آدم", "راجعي وسيم",
             "أوراري يوسف", "توم ابراهيم", "الساحلي جعفر", "والي أسامة", "واعر أكرم", "بوراس آدم", "حسيد أنيس"]
WED_NAMES = [] if not SEEDED else ["حميدو عبد الباري", "زرور مهدي", "طمار أمين", "بوشامة عبد الرؤوف", "قبلي هيثم", "بوغطان عبد الهادي",
             "صافري علي", "والي أنس", "زارب عماد", "لعصيص مصعب", "حسيد أنيس"]
MDAYS = {"sat": ("السبت", 5), "sun": ("الأحد", 6), "tue": ("الثلاثاء", 1), "wed": ("الأربعاء", 2)}  # أيام المراجعة
MFOJ = {"A": "sat,tue", "B": "sun,wed"}  # الفوج الأول: السبت والثلاثاء، الفوج الثاني: الأحد والأربعاء
REV_SHEIKH = {"1": DIR_N} if SOLO else {"1": REV1_N, "2": REV2_N}
MAX_JUST = 3  # أقصى عدد تبريرات يجريها الولي في الشهر الواحد
ATT = {"p": "حاضر", "l": "حاضر متأخر", "a": "غائب", "e": "غائب بعذر"}
LATE_W = 0.5  # وزن الحضور المتأخر مقابل الحضور الكامل
CLASS_WD = {5, 6, 1, 2}  # أيام الدراسة: السبت والأحد والثلاثاء والأربعاء (لا دراسة الاثنين والخميس والجمعة)


def norm_name(t):
    t = "".join(ch for ch in t if ch.isalpha() or ch == " ")
    for a, b in (("أ", "ا"), ("إ", "ا"), ("آ", "ا"), ("ى", "ي"), ("ة", "ه"), ("ؤ", "و"), ("ئ", "ي")):
        t = t.replace(a, b)
    return " ".join(t.split())


def match_student(name, students):
    import difflib
    n = norm_name(name)
    best, sc = None, 0.0
    for s in students:
        m = norm_name(s["name"])
        r = 1.0 if set(m.split()) == set(n.split()) else difflib.SequenceMatcher(None, n, m).ratio()
        if r > sc:
            best, sc = s, r
    return best if sc >= 0.84 else None


def _wd(d):
    try:
        return dt.date.fromisoformat(d[:10]).weekday()
    except ValueError:
        return -1


def days_of(s):
    return [d for d in (s.get("days") or "").split(",") if d in DAYS]


def mdays_of(s):
    return [d for d in (s.get("mdays") or "").split(",") if d in MDAYS]


def next_hifz(days, table=None):
    table = table or DAYS
    t = dt.datetime.now(TZ).date()
    for k in range(0, 8):
        d = t + dt.timedelta(days=k)
        for key in days:
            if table[key][1] == d.weekday():
                return d, k
    return None, None


def names_of(codes, table):
    return " و".join(table[k][0] for k in codes)


def now():
    return dt.datetime.now(TZ)


def today():
    return now().date().isoformat()


def sha(u, p):
    return hashlib.sha256(f"furqan:{u}:{p}".encode()).hexdigest()


def secret(k, default=""):
    try:
        return st.secrets[k]
    except Exception:
        return default


def staff_hashes():
    try:
        return {**DEFAULT_HASHES, **dict(st.secrets["staff"])}
    except Exception:
        return DEFAULT_HASHES


# ───────────────────────── التخزين ─────────────────────────
class LocalStore:
    """تخزين تجريبي في ملفات CSV (يُمحى على Streamlit Cloud عند إعادة التشغيل)."""

    def __init__(self, d=None):
        self.d = d or os.path.join(HERE, "data")
        os.makedirs(self.d, exist_ok=True)

    def _p(self, n):
        return os.path.join(self.d, f"{n}.csv")

    def list(self, n):
        if not os.path.exists(self._p(n)):
            return []
        with open(self._p(n), newline="", encoding="utf-8") as f:
            rows = [dict(r) for r in csv.DictReader(f)]
        for r in rows:
            for k in HEAD[n]:
                r.setdefault(k, "")
        return rows

    def _save(self, n, rows):
        with open(self._p(n), "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=HEAD[n])
            w.writeheader()
            for r in rows:
                w.writerow({k: r.get(k, "") for k in HEAD[n]})

    def add(self, n, row):
        rows = self.list(n)
        row = {**row, "id": uuid.uuid4().hex}
        rows.append(row)
        self._save(n, rows)
        return row["id"]

    def add_many(self, n, rows):
        return [self.add(n, r) for r in rows]

    def update(self, n, id_, fields):
        self.update_many(n, {id_: fields})

    def update_many(self, n, changes):
        rows = self.list(n)
        for r in rows:
            if r["id"] in changes:
                r.update({k: str(v) for k, v in changes[r["id"]].items()})
        self._save(n, rows)

    def delete(self, n, id_):
        self._save(n, [r for r in self.list(n) if r["id"] != id_])

    def delete_by_sid(self, n, sid):
        self._save(n, [r for r in self.list(n) if r.get("sid") != sid])

    def delete_many(self, n, ids):
        ids = set(ids)
        self._save(n, [r for r in self.list(n) if r["id"] not in ids])


class SheetsStore:
    """التخزين الدائم في Google Sheets. يتبع أعمدة الجدول الفعلية بأسمائها ويضيف الناقص منها."""

    def __init__(self, gc, url, names=None):
        self.sh = gc.open_by_url(url)
        self._w, self._h = {}, {}
        self.names = list(names) if names else None  # أوراق محددة فقط (للجدول المركزي)

    def _open(self, n):
        import gspread

        if n in self._w:
            return self._w[n], self._h[n]
        try:
            w = self.sh.worksheet(n)
        except gspread.WorksheetNotFound:
            w = self.sh.add_worksheet(title=n, rows=1000, cols=max(len(HEAD[n]), 10))
        h = [c.strip() for c in w.row_values(1)]
        if not h:
            h = list(HEAD[n])
            w.update(values=[h], range_name="A1", raw=True)
        else:
            missing = [c for c in HEAD[n] if c not in h]
            if missing:
                if len(h) + len(missing) > w.col_count:
                    w.add_cols(len(h) + len(missing) - w.col_count)
                h = h + missing
                w.update(values=[h], range_name="A1", raw=True)
        self._w[n], self._h[n] = w, h
        return w, h

    def _fetch_all(self):
        """يقرأ كل الأوراق بطلب واحد إلى Google بدل طلب لكل ورقة (أسرع بكثير وأخف على حدّ 60 طلبا في الدقيقة)."""
        if not getattr(self, "_ok", False):
            for n in (self.names or HEAD):  # يضمن وجود كل ورقة وأعمدتها
                self._open(n)
            self._ok = True
        names = list(self.names or HEAD)
        res = self.sh.values_batch_get([f"'{n}'" for n in names])
        out = {}
        for n, vr in zip(names, res.get("valueRanges", [])):
            vals = vr.get("values", [])
            h = [str(c).strip() for c in vals[0]] if vals else list(HEAD[n])
            rows = []
            for r in vals[1:]:
                if not any(str(c).strip() for c in r):
                    continue
                d = {k: (str(r[i]) if i < len(r) else "") for i, k in enumerate(h) if k}
                for k in HEAD[n]:
                    d.setdefault(k, "")
                rows.append(d)
            out[n] = rows
        self._snap = (time.time(), out)
        return self._snap

    def list(self, n):
        snap = getattr(self, "_snap", None)
        if snap is None or time.time() - snap[0] > 3:  # أوراق التحديث نفسه تتشارك لقطة واحدة
            snap = self._fetch_all()
        if n in snap[1]:
            return [dict(r) for r in snap[1][n]]
        return self._list_one(n)

    def _list_one(self, n):
        w, h = self._open(n)
        out = []
        for r in w.get_all_records(numericise_ignore=["all"]):
            d = {k: str(v) for k, v in r.items()}
            for k in HEAD[n]:
                d.setdefault(k, "")
            out.append(d)
        return out

    def _append(self, w, h, rows):
        """يكتب الصفوف في أول سطر فارغ بعد آخر بيانات في الورقة (بدل الاعتماد على كشف الجدول التلقائي)،
        ثم يتحقق أن الصف الأخير قُرئ فعلا من الورقة."""
        vals = w.get_all_values()
        r = len(vals) + 1
        need = r + len(rows) - 1
        if need > w.row_count:
            w.add_rows(max(200, need - w.row_count + 50))
        w.update(values=rows, range_name=f"A{r}", raw=True)
        ic = h.index("id")
        back = w.row_values(r + len(rows) - 1)
        if len(back) <= ic or back[ic] != rows[-1][ic]:
            raise RuntimeError("لم يُثبَّت التسجيل في جدول Google بعد الكتابة")

    def add(self, n, row):
        w, h = self._open(n)
        row = {**row, "id": uuid.uuid4().hex}
        self._append(w, h, [[str(row.get(k, "")) for k in h]])
        return row["id"]

    def add_many(self, n, rows):
        w, h = self._open(n)
        out = [[str(r.get(k, "")) for k in h] for r in rows]
        ids = []
        for row in out:  # كل صف يأخذ معرّفاً مختلفاً
            ids.append(uuid.uuid4().hex)
            row[h.index("id")] = ids[-1]
        if out:
            self._append(w, h, out)
        return ids

    def diagnose(self):
        """معلومات تشخيصية عن الورقتين الأهم، لتصوير الخلل إن وُجد."""
        out = []
        for n in ("logs", "students"):
            w, h = self._open(n)
            v = w.get_all_values()
            out.append(f"{n}: {len(v) - 1} صفًا، {len(h)} عمودًا، حجم الشبكة {w.row_count}×{w.col_count}")
            out.append("   العناوين: " + " | ".join(h))
            blanks = sum(1 for r in v[1:] if not any(c.strip() for c in r))
            noid = sum(1 for r in v[1:] if any(c.strip() for c in r) and (h.index("id") >= len(r) or not r[h.index("id")].strip()))
            out.append(f"   صفوف فارغة: {blanks} · صفوف بلا معرّف: {noid}")
        return out

    def update_many(self, n, changes):
        """تحديث عدة صفوف بطلب كتابة واحد (لتفادي حدود Google: 60 طلباً في الدقيقة)."""
        w, h = self._open(n)
        vals = w.get_all_values()
        ic = h.index("id")
        batch = []
        for r, row in enumerate(vals[1:], start=2):
            if ic < len(row) and row[ic] in changes:
                row = list(row) + [""] * (len(h) - len(row))
                for k, v in changes[row[ic]].items():
                    row[h.index(k)] = str(v)
                batch.append({"range": f"A{r}", "values": [row]})
        if batch:
            w.batch_update(batch, raw=True)

    def _row(self, w, h, id_):
        c = w.find(id_, in_column=h.index("id") + 1)
        return c.row if c else None

    def update(self, n, id_, fields):
        w, h = self._open(n)
        r = self._row(w, h, id_)
        if not r:
            return
        vals = w.row_values(r)
        vals += [""] * (len(h) - len(vals))
        for k, v in fields.items():
            vals[h.index(k)] = str(v)
        w.update(values=[vals], range_name=f"A{r}", raw=True)

    def delete(self, n, id_):
        w, h = self._open(n)
        r = self._row(w, h, id_)
        if r:
            w.delete_rows(r)

    def delete_many(self, n, ids):
        """حذف عدة صفوف بطلب واحد."""
        w, h = self._open(n)
        ids = set(ids)
        vals = w.get_all_values()
        ic = h.index("id")
        rows = [r for r, row in enumerate(vals[1:], start=2) if ic < len(row) and row[ic] in ids]
        if rows:
            reqs = [{"deleteDimension": {"range": {"sheetId": w.id, "dimension": "ROWS", "startIndex": r - 1, "endIndex": r}}}
                    for r in sorted(rows, reverse=True)]
            self.sh.batch_update({"requests": reqs})

    def delete_by_sid(self, n, sid):
        w, h = self._open(n)
        vals = w.col_values(h.index("sid") + 1)
        for i in range(len(vals), 1, -1):
            if vals[i - 1] == sid:
                w.delete_rows(i)


def _invalidates(fn):
    def wrapper(self, *a, **k):
        try:
            return fn(self, *a, **k)
        finally:
            self._snap = None  # أي كتابة تُبطل اللقطة المقروءة

    return wrapper


for _m in ("_append", "update_many", "update", "delete", "delete_many", "delete_by_sid"):
    setattr(SheetsStore, _m, _invalidates(getattr(SheetsStore, _m)))


@st.cache_resource
def _sheets_store(url, sa_json):
    import json

    import gspread

    return SheetsStore(gspread.service_account_from_dict(json.loads(sa_json)), url)


@st.cache_resource
def _central_store(url, sa_json):
    import json

    import gspread

    return SheetsStore(gspread.service_account_from_dict(json.loads(sa_json)), url, names=["sug"])


def _central():
    """جدول الاقتراحات المركزي المشترك بين الأقسام (اختياري: central_sheet_url في Secrets). بدونه تبقى الاقتراحات في جدول القسم."""
    try:
        url = str(st.secrets["central_sheet_url"]).strip()
    except Exception:
        return None
    if not url:
        return None
    if url.startswith("local:"):  # للاختبارات
        return LocalStore(url[6:])
    try:
        import json

        sa = {k: str(v) for k, v in dict(st.secrets["gcp_service_account"]).items()}
        return _central_store(url, json.dumps(sa))
    except Exception as e:
        st.session_state["_central_err"] = f"{type(e).__name__}"
        return None


@st.cache_data(ttl=30, show_spinner=False)
def _cload(sk=""):
    c = _central()
    return c.list("sug") if c is not None else []


def _local():
    return LocalStore(os.path.join(HERE, "data", SECKEY)) if MULTI else LocalStore()


def get_store():
    """يعيد (المخزن، دائم؟، سبب الوضع التجريبي). لا يخزّن الوضع التجريبي أبداً في الذاكرة المؤقتة."""
    import json

    try:
        sa = {k: str(v) for k, v in dict(st.secrets["gcp_service_account"]).items()}
        url = str(_SC.get("sheet_url") or st.secrets["sheet_url"]) if MULTI else str(st.secrets["sheet_url"])
    except KeyError:
        return _local(), False, "ينقص في Secrets قسم [gcp_service_account] أو السطر sheet_url"
    except Exception as e:
        if type(e).__name__ == "StreamlitSecretNotFoundError":
            return _local(), False, "لم يجد التطبيق أي Secrets محفوظة"
        st.error(f"خطأ في قراءة Secrets ({type(e).__name__}). غالباً علامة تنصيص ناقصة أو سطر مكسور.")
        st.stop()
    return _sheets_store(url, json.dumps(sa)), True, ""


try:
    STORE, PERSISTENT, LOCAL_REASON = (None, True, "") if GENERIC else get_store()
except Exception as e:  # الإعدادات موجودة لكن الاتصال فشل: لا نعمل ببيانات مؤقتة أبداً
    st.error(f"تعذّر الاتصال بجدول Google Sheets ({type(e).__name__}): {str(e)[:200]}")
    st.stop()


@st.cache_data(ttl=30, show_spinner=False)
def _load(n, sk=""):
    return STORE.list(n)


def explain(e):
    """نص الخطأ من Google بدون أي بيانات سرية (Streamlit يخفي الأخطاء غير المعالجة)."""
    resp = getattr(e, "response", None)
    if resp is not None:
        try:
            j = resp.json()["error"]
            return f'{j.get("code")} {j.get("status")}: {str(j.get("message"))[:300]}'
        except Exception:
            return f"HTTP {getattr(resp, 'status_code', '?')}"
    return f"{type(e).__name__}: {str(e)[:200]}"


def load(n):
    try:
        return _load(n, SECKEY)
    except Exception as e:
        st.error(f"تعذّرت قراءة الورقة «{n}» من Google Sheets — {explain(e)}")
        st.stop()


def write(fn, *a):
    r = fn(*a)
    _load.clear()
    return r


def who():
    me = st.session_state.get("me")
    return TEACHERS[me]["n"] if me is not None else "ولي الأمر"


def audit(act, detail="", by=None):
    """سجل التعديلات: من فعل ماذا ومتى. لا يُوقف العمل إن فشلت الكتابة."""
    try:
        STORE.add("audit", {"ts": now().strftime("%Y-%m-%d %H:%M"), "who": by or who(), "act": act, "detail": str(detail)[:300]})
    except Exception:
        pass


def cfg_get(k, d=""):
    return next((r["val"] for r in load("cfg") if r["key"] == k), d)


def cfg_set(k, v):
    r = next((r for r in load("cfg") if r["key"] == k), None)
    if r:
        write(STORE.update, "cfg", r["id"], {"val": str(v)})
    else:
        write(STORE.add, "cfg", {"key": k, "val": str(v)})


# ───────────────────────── الحماية من التخمين ─────────────────────────
@st.cache_resource
def _fails():
    return []


def blocked():
    t = time.time()
    f = _fails()
    f[:] = [x for x in f if t - x < 600]
    return len(f) >= 30


def note_fail():
    _fails().append(time.time())


# ───────────────────────── التنسيق ─────────────────────────
THEME_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Amiri:wght@400;700&family=Reem+Kufi:wght@500;600;700&display=swap');
:root{
  --ink:#0a4a3e;--night:#06352c;--gold:#a9822a;--gold2:#d4af37;--paper:#f3f5ee;--panel:#fbfcf8;
  --tx:#1c2a25;--mut:#5f6f67;--line:#d6ddcb;
  --disp:'Reem Kufi','Noto Kufi Arabic','Tajawal',sans-serif;
  --body:'Amiri','Noto Naskh Arabic','Traditional Arabic',serif;
  --pat:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='48' height='48' viewBox='0 0 48 48'%3E%3Cg fill='none' stroke='%23d4af37' stroke-opacity='.22' stroke-width='1'%3E%3Crect x='12' y='12' width='24' height='24'/%3E%3Crect x='12' y='12' width='24' height='24' transform='rotate(45 24 24)'/%3E%3C/g%3E%3C/svg%3E");
}
.stApp{background:var(--paper);color:var(--tx);direction:rtl}
.stApp, .stApp :not(span[data-testid="stIconMaterial"]){font-family:var(--body)!important}
.stApp p,.stApp label,.stApp li,[data-testid="stMarkdownContainer"],[data-testid="stWidgetLabel"],
[data-testid="stCaptionContainer"],[data-testid="stAlert"]{direction:rtl;text-align:right}
[data-testid="stWidgetLabel"] p{font-size:1.02rem;color:var(--ink)}
[data-testid="stHorizontalBlock"]{direction:rtl}
input,textarea{direction:rtl;text-align:right}
[data-baseweb="popover"],[data-baseweb="menu"]{direction:rtl;font-family:var(--body)}
.block-container{max-width:700px;padding:2.4rem 1rem 3rem}
[data-testid="stHeaderActionElements"],#MainMenu,footer,[data-testid="stToolbar"],[data-testid="stDecoration"]{display:none!important}
header[data-testid="stHeader"]{background:transparent;height:0}

/* الشريط العلوي: لوحة العنوان في المصحف */
.cart{position:relative;display:flex;align-items:center;gap:14px;padding:14px 16px;border-radius:14px;color:#f6efcf;
  background:var(--pat),linear-gradient(135deg,var(--night),var(--ink));
  box-shadow:0 0 0 3px var(--paper),0 0 0 4px var(--gold2);margin:4px 4px 20px}
.cart .lg{flex:none;width:62px;height:62px;border-radius:12px;background:#fff;padding:3px;border:2px solid var(--gold2);
  display:flex;align-items:center;justify-content:center}
.cart .lg img{width:100%;height:100%;object-fit:contain;border-radius:8px}
.cart .t1,.disp{font-family:var(--disp)!important}
.cart .t1{font-weight:700;font-size:1.28rem;line-height:1.4;color:#fbf3d2}
.cart .t2{font-size:1rem;color:#cfe0d6;margin-top:2px}

/* النجمة الثمانية */
.med{flex:none;position:relative;display:inline-block;width:12px;height:12px}
.med::before,.med::after{content:"";position:absolute;inset:1px;border:1.5px solid var(--gold)}
.med::after{transform:rotate(45deg)}

/* عناوين الأقسام */
.sec{display:flex;align-items:center;gap:10px;margin:24px 0 10px}
.sec .ttl{white-space:nowrap;font-family:var(--disp)!important;font-weight:600;font-size:1.04rem;color:var(--ink)}
.sec .rule{flex:1;height:1px;background:linear-gradient(to left,var(--gold2),transparent)}

.chip,.bd{font-family:var(--disp)!important;font-size:.78rem;color:var(--gold);border:1px solid var(--gold);border-radius:99px;padding:1px 10px;white-space:nowrap}
.hi{display:flex;align-items:center;gap:10px;font-family:var(--disp)!important;font-size:1.05rem;color:var(--ink);padding-top:6px}
.bsm{text-align:center;font-size:1.55rem;color:var(--ink);margin:0 0 12px;line-height:1.6}
.mut{color:var(--mut)}
.lead{color:var(--mut);margin:0 0 14px;font-size:1.08rem}
.foot{text-align:center;color:var(--mut);margin-top:28px;padding-top:12px;border-top:1px solid var(--line)}

/* اسم الطالب */
.stu{display:flex;align-items:center;gap:12px;margin:6px 0 14px}
.stu .nmx{font-family:var(--disp)!important;font-weight:700;font-size:1.7rem;color:var(--ink);text-align:center;line-height:1.4}
.stu .ln{flex:1;height:1px;background:linear-gradient(to left,var(--gold2),transparent)}
.stu .ln:last-child{background:linear-gradient(to right,var(--gold2),transparent)}

/* الحضور والاشتراك */
.trio{display:grid;grid-template-columns:repeat(3,1fr);border-top:1px solid var(--line);border-bottom:1px solid var(--line);margin:6px 0 12px}
.trio div{text-align:center;padding:12px 4px}
.trio div+div{border-inline-start:1px solid var(--line)}
.trio b{display:block;font-family:var(--disp)!important;font-size:2.1rem;line-height:1.15;font-weight:700}
.trio span{font-size:1rem;color:var(--mut)}
.bub{border:1px solid var(--line);border-radius:12px;padding:8px 14px;margin:6px 0;background:#fff;max-width:90%;line-height:1.8}
.bub.me{background:#eef4e8;border-color:#c7d8b8;margin-inline-start:auto}
.bub .mt{font-family:var(--disp)!important;font-size:.78rem;color:var(--mut);margin-bottom:2px}
.bub.new{border-color:var(--gold);box-shadow:0 0 0 2px #f1e4b6}
.note{background:#fbf6e6;border:1px solid #e6d9a8;border-right:4px solid var(--gold);border-radius:10px;padding:10px 14px;margin:8px 0 14px;color:#5a4710;font-size:1.02rem;line-height:1.9}
.pay{padding:10px 14px;border-radius:10px;font-family:var(--disp)!important;font-size:.95rem;margin-bottom:6px;border:1px solid}
.pay.ok{background:#e4f1e8;border-color:#b9d9c5;color:#145c3a}
.pay.no{background:#f7e8e4;border-color:#e6c4bb;color:#8a3326}
.c-ok{color:#1e7a4f}.c-no{color:#a64b3c}.c-ex{color:#a8841f}

/* سجلات الحفظ والمراجعة */
.ent{display:flex;gap:12px;align-items:flex-start;padding:12px 2px;border-top:1px solid var(--line)}
.ent:first-child{border-top:0}
.ent .med{margin-top:11px}
.ent .bd2{flex:1;min-width:0}
.ent .txt{font-size:1.22rem;line-height:1.7;color:var(--tx)}
.ent .meta{display:flex;flex-wrap:wrap;font-family:var(--disp)!important;font-size:.78rem;color:var(--mut)}
.ent .meta span{font-family:var(--disp)!important}
.ent .meta span+span::before{content:"";display:inline-block;width:1px;height:.85em;background:currentColor;opacity:.4;margin:0 .6em;vertical-align:-1px}
.gr{flex:none;font-family:var(--disp)!important;font-size:.8rem;font-weight:600;padding:3px 10px;border-radius:99px;margin-top:7px;white-space:nowrap}
.g1{background:#dcefe3;color:#145c3a}.g2{background:#d9eeea;color:#17695f}.g3{background:#f3ead0;color:#7a5d12}
.g4{background:#f7e5cc;color:#8a5410}.g5{background:#f3d9d3;color:#8a3326}
.empty{padding:18px 4px;color:var(--mut);font-size:1.1rem}

/* تقرير المشايخ */
.rep{padding:14px 2px 6px;border-top:1px solid var(--line)}
.rep .top{display:flex;justify-content:space-between;align-items:center}
.rep .nm{font-family:var(--disp)!important;font-weight:600;font-size:1.1rem;color:var(--ink);display:flex;align-items:center;gap:10px}
.rep .pc{font-family:var(--disp)!important;font-weight:700;font-size:1.9rem;line-height:1;color:var(--ink)}
.rep .pc small{font-family:var(--disp)!important;font-size:.95rem;color:var(--gold);margin-inline-start:2px}
.chal{background:linear-gradient(135deg,var(--ink),#0e6354);color:#f3e7b8;border-radius:14px;padding:11px 14px;margin:10px 0 12px;border:1px solid #d4af37}
.chal .ct{font-family:var(--disp)!important;font-weight:600;font-size:1.02rem;display:flex;justify-content:space-between;gap:8px;color:#fff}
.chal .ct small{color:#f3e7b8;font-size:.82rem;font-weight:400}
.chal .cl{display:flex;flex-wrap:wrap;gap:6px;margin:8px 0 4px}
.chal .ci{padding:3px 10px;border-radius:99px;font-size:.84rem;background:#12614f;color:#dfe9e2}
.chal .ci.ok{background:#d4af37;color:#2a2005;font-weight:600}.chal .ci.bad{background:#b3261e;color:#fff}
.chal .cm{font-size:.78rem;opacity:.85}
.qmap{display:grid;grid-template-columns:repeat(auto-fill,minmax(31px,1fr));gap:4px;direction:rtl;margin:8px 0}
.mc{display:flex;align-items:center;justify-content:center;height:27px;border-radius:6px;font-size:.72rem;font-family:var(--disp)!important}
.mfull{background:var(--ink);color:#fff}.mpart{background:var(--gold2);color:#3a2d08}.mnone{background:#e6eadf;color:#8a978f}
.mc.mpart{outline:2px dashed rgba(255,255,255,.8);outline-offset:-4px}
.mc.f0{background:#0a4a3e;color:#fff}.mc.f1{background:#4c9a74;color:#fff}.mc.f2{background:#e0b94a;color:#3a2d08}.mc.f3{background:#c8423a;color:#fff}.mc.f4{background:#b7c6d6;color:#2a3a4a}
.lg-f{display:inline-block;width:11px;height:11px;border-radius:3px;margin:0 3px 0 2px;vertical-align:-1px}
.bar{height:7px;background:#dfe6d6;border-radius:99px;overflow:hidden;margin:9px 0 6px}
.bar i{display:block;height:100%;border-radius:99px;background:linear-gradient(to left,var(--ink),var(--gold2))}
.rep .sub{font-size:1rem;color:var(--mut)}

/* عناصر Streamlit */
[data-testid="stTextInputRootElement"],[data-testid="stTextAreaRootElement"],[data-testid="stDateInputField"],[data-testid="stNumberInputContainer"],
[data-testid="stSelectbox"] [role="group"],[data-baseweb="input"],[data-baseweb="base-input"],[data-baseweb="textarea"],[data-baseweb="select"]>div{
  background:#fff!important;border:1px solid #c5ceb8!important;border-radius:10px!important}
[data-testid="stTextInputRootElement"]:focus-within,[data-testid="stTextAreaRootElement"]:focus-within,[data-testid="stDateInputField"]:focus-within,
[data-testid="stSelectbox"] [role="group"]:focus-within,[data-baseweb="input"]:focus-within,[data-baseweb="textarea"]:focus-within{
  border-color:var(--ink)!important;box-shadow:0 0 0 3px rgba(10,74,62,.14)!important}
[data-testid="stTextInputRootElement"] input,[data-testid="stTextAreaRootElement"] textarea,[data-testid="stSelectbox"] input{background:transparent!important}
button[data-testid^="stBaseButton"]{font-family:var(--disp)!important;font-weight:600;border-radius:10px;min-height:44px;border:1px solid #c5ceb8;background:var(--panel);color:var(--ink);transition:background .15s,border-color .15s}
button[data-testid^="stBaseButton"]:hover{border-color:var(--gold);color:var(--ink)}
button[data-testid="stBaseButton-primary"],button[data-testid="stBaseButton-primaryFormSubmit"]{background:var(--ink);color:#f6efcf;border-color:var(--ink)}
button[data-testid="stBaseButton-primary"]:hover,button[data-testid="stBaseButton-primaryFormSubmit"]:hover{background:#0d5c4d;border-color:var(--gold2);color:#fff}
button[data-testid^="stBaseButton"]:focus-visible{outline:2px solid var(--gold2);outline-offset:2px}
[data-testid="stTab"] p,button[data-baseweb="tab"]{font-family:var(--disp)!important;font-weight:600;font-size:1rem;color:var(--mut)}
[data-testid="stTab"][data-selected="true"] p,button[data-baseweb="tab"][aria-selected="true"]{color:var(--ink)}
[data-testid="stTab"]>div:not([data-testid]){background:var(--gold2)!important;height:3px!important}
[data-baseweb="tab-highlight"]{background:var(--gold2)!important;height:3px!important}
[data-baseweb="tab-border"]{background:var(--line)!important}
[data-testid="stExpander"] details{border:1px solid var(--line);border-radius:12px;background:var(--panel)}
[data-testid="stExpander"] summary{font-family:var(--disp)!important;font-size:.95rem}
[data-testid="stForm"]{border:1px solid var(--line);border-radius:14px;background:var(--panel);padding:14px}
[data-testid="stAlert"]{border-radius:12px}
</style>
"""
st.markdown(THEME_CSS, unsafe_allow_html=True)


@st.cache_resource
def _logo_uri():
    import base64

    p = os.path.join(HERE, "logo.jpg")
    if not os.path.exists(p):
        return ""
    with open(p, "rb") as f:
        return "data:image/jpeg;base64," + base64.b64encode(f.read()).decode()


def header(sub=None, basmala=False):
    sub = sub or SEC
    if basmala:
        st.markdown('<div class="bsm">بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ</div>', unsafe_allow_html=True)
    uri = _logo_uri()
    img = f'<div class="lg"><img src="{uri}" alt=""></div>' if uri else ""
    st.markdown(
        f'<div class="cart">{img}<div><div class="t1">{ASSOC}</div><div class="t2">{sub}</div></div></div>',
        unsafe_allow_html=True,
    )
    if not PERSISTENT:
        st.warning(f"وضع تجريبي: البيانات مؤقتة وتُمحى عند إعادة التشغيل. السبب: {LOCAL_REASON}.")


def sec(t):
    st.markdown(f'<div class="sec"><i class="med"></i><div class="ttl">{t}</div><span class="rule"></span></div>', unsafe_allow_html=True)


def esc(s):
    return (str(s or "")).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


GCLS = {"لم يحفظ": "g5", "ممتاز": "g1", "جيد جدا": "g2", "جيد": "g3", "متوسط": "g4", "يحتاج إعادة": "g5"}


KIND_TAG = {"rep": "تكرار", "old": "إعادة قديمة", "none": "لم يحفظ"}


_AR_DIG = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹–—", "01234567890123456789--")


def parse_err(txt, sn, a1, a2, en=0):
    """يحوّل أرقام الآيات (مثل «12، 14-16») إلى «سورة:آية,…». يعيد (النص المخزَّن، رسالة الخطأ)."""
    txt = (txt or "").translate(_AR_DIG).strip()
    if not txt:
        return "", ""
    if en and en != sn:
        return "", "حدّد آيات التعثّر فقط عند تسجيل مقطع في سورة واحدة"
    ks = set()
    for t in re.split(r"[,\s،;؛]+", txt):
        if not t:
            continue
        m = re.fullmatch(r"(\d+)(?:-(\d+))?", t)
        if not m:
            return "", f"«{t}» ليس رقم آية صحيحا في خانة آيات التعثّر"
        x, y = int(m.group(1)), int(m.group(2) or m.group(1))
        ks |= set(range(min(x, y), max(x, y) + 1))
    bad = [k for k in sorted(ks) if not (a1 <= k <= a2)]
    if bad:
        return "", f"الآية {bad[0]} خارج المقطع المسجَّل (من {a1} إلى {a2})"
    if len(ks) > 60:
        return "", "عدد آيات التعثّر كبير جدا"
    return ",".join(f"{sn}:{k}" for k in sorted(ks)), ""


def err_pairs(l):
    out = []
    for t in (l.get("err") or "").split(","):
        try:
            a, b = t.split(":")
            out.append((int(a), int(b)))
        except ValueError:
            pass
    return out


def err_text(pairs):
    by = {}
    for sn, k in sorted(pairs):
        by.setdefault(sn, []).append(k)
    return "؛ ".join(f"{SURAHS[sn - 1][0]} آية " + "، ".join(map(str, ks)) for sn, ks in by.items())


def err_counts(logs, sid=None, since=None):
    """(سورة، آية) ← التسجيلات التي تعثّر فيها الطالب."""
    out = {}
    for l in logs:
        if (sid and l["sid"] != sid) or (since and l["date"] < since):
            continue
        for p in err_pairs(l):
            out.setdefault(p, []).append(l)
    return out


def err_top(logs, sid, n=4, days=120):
    c = err_counts(logs, sid, _ago(today(), days))
    items = sorted(c.items(), key=lambda kv: max(x["date"] for x in kv[1]), reverse=True)
    items = sorted(items, key=lambda kv: len(kv[1]), reverse=True)[:n]
    return [(sn, k, len(v)) for (sn, k), v in items]


def err_top_text(top):
    return "، ".join(f"{SURAHS[sn - 1][0]} آية {k}" + (f" ({c} مرات)" if c > 1 else "") for sn, k, c in top)


def err_hint(logs, sid, aset, days=120):
    """أخطاء سابقة للطالب داخل مقطع معيّن (مجموعة (سورة، آية))، نصا."""
    c = err_counts(logs, sid, _ago(today(), days))
    hit = sorted((p, v) for p, v in c.items() if p in aset)
    return "، ".join(f"{SURAHS[sn - 1][0]} آية {k}" + (f" ({len(v)} مرات)" if len(v) > 1 else "") for (sn, k), v in hit)


def flash_add(msg):
    st.session_state.setdefault("_flash", []).append(msg)


def flash_show():
    for m_ in st.session_state.pop("_flash", []):
        st.warning(m_)


def err_class_ui(students, logs):
    """آيات تعثّر فيها أكثر من طالب هذا الشهر (للحلقة كلها)."""
    nm = {x["id"]: x["name"] for x in students}
    c = err_counts([l for l in logs if l["sid"] in nm], None, _ago(today(), 30))
    rows = sorted(((len({x["sid"] for x in v}), p, v) for p, v in c.items() if len({x["sid"] for x in v}) >= 2), key=lambda r: (-r[0], r[1]), reverse=False)
    with st.expander(f"آيات تعثّرت فيها الحلقة هذا الشهر ({len(rows)})"):
        if not rows:
            st.caption("لا آية تعثّر فيها أكثر من طالب في آخر 30 يوما. تُسجَّل آيات التعثّر عند حفظ التسجيل.")
        for n_, (sn, k), v in rows[:10]:
            names = "، ".join(sorted({nm[x["sid"]] for x in v}))
            st.markdown(f"**سورة {SURAHS[sn - 1][0]} آية {k}**: تعثّر فيها {n_} طلبة — {esc(names)}")


def logs_html(L, empty="لا توجد تسجيلات بعد."):
    if not L:
        return f'<div class="empty">{empty}</div>'
    out = []
    for l in L:
        mur = l.get("type") != "hifz"
        tag = KIND_TAG.get(l.get("kind", "")) if not mur else None
        metas = [l.get("date"), l.get("teacher"), tag] + ([] if mur else [l.get("note")])
        meta = "".join(f"<span>{esc(x)}</span>" for x in metas if x)
        redo = f'<div class="meta"><span style="color:#b3261e">🔁 المطلوب إعادته / الأخطاء: {esc(l["note"])}</span></div>' if mur and l.get("note") else ""
        ep_ = err_pairs(l)
        if ep_:
            redo += f'<div class="meta"><span style="color:#b3261e">⚠ تعثّر في: {esc(err_text(ep_))}</span></div>'
        out.append(
            f'<div class="ent"><i class="med"></i><div class="bd2"><div class="txt">{esc(l["detail"])}</div>'
            f'<div class="meta">{meta}</div>{redo}</div><span class="gr {GCLS.get(l["grade"], "g3")}">{esc(l["grade"])}</span></div>'
        )
    return "".join(out)


def by_date(rows):
    return sorted(rows, key=lambda x: (x.get("date", ""), x.get("ts", "")), reverse=True)


# ───────────────────────── التقرير الشهري (PDF) ─────────────────────────
WEEKDAYS_AR = ["الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت", "الأحد"]
MONTHS_AR = ["جانفي", "فيفري", "مارس", "أفريل", "ماي", "جوان", "جويلية", "أوت", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"]
DISC = {3: "منضبط", 2: "متوسط", 1: "غير منضبط"}
GPTS = {"لم يحفظ": 0, "ممتاز": 5, "جيد جدا": 4, "جيد": 3, "متوسط": 2, "يحتاج إعادة": 1}
FONT = os.path.join(HERE, "Amiri-Regular.ttf")


SURAHS = [("الفاتحة", 7), ("البقرة", 286), ("آل عمران", 200), ("النساء", 176), ("المائدة", 120), ("الأنعام", 165), ("الأعراف", 206), ("الأنفال", 75), ("التوبة", 129), ("يونس", 109),
          ("هود", 123), ("يوسف", 111), ("الرعد", 43), ("إبراهيم", 52), ("الحجر", 99), ("النحل", 128), ("الإسراء", 111), ("الكهف", 110), ("مريم", 98), ("طه", 135),
          ("الأنبياء", 112), ("الحج", 78), ("المؤمنون", 118), ("النور", 64), ("الفرقان", 77), ("الشعراء", 227), ("النمل", 93), ("القصص", 88), ("العنكبوت", 69), ("الروم", 60),
          ("لقمان", 34), ("السجدة", 30), ("الأحزاب", 73), ("سبأ", 54), ("فاطر", 45), ("يس", 83), ("الصافات", 182), ("ص", 88), ("الزمر", 75), ("غافر", 85),
          ("فصلت", 54), ("الشورى", 53), ("الزخرف", 89), ("الدخان", 59), ("الجاثية", 37), ("الأحقاف", 35), ("محمد", 38), ("الفتح", 29), ("الحجرات", 18), ("ق", 45),
          ("الذاريات", 60), ("الطور", 49), ("النجم", 62), ("القمر", 55), ("الرحمن", 78), ("الواقعة", 96), ("الحديد", 29), ("المجادلة", 22), ("الحشر", 24), ("الممتحنة", 13),
          ("الصف", 14), ("الجمعة", 11), ("المنافقون", 11), ("التغابن", 18), ("الطلاق", 12), ("التحريم", 12), ("الملك", 30), ("القلم", 52), ("الحاقة", 52), ("المعارج", 44),
          ("نوح", 28), ("الجن", 28), ("المزمل", 20), ("المدثر", 56), ("القيامة", 40), ("الإنسان", 31), ("المرسلات", 50), ("النبأ", 40), ("النازعات", 46), ("عبس", 42),
          ("التكوير", 29), ("الانفطار", 19), ("المطففين", 36), ("الانشقاق", 25), ("البروج", 22), ("الطارق", 17), ("الأعلى", 19), ("الغاشية", 26), ("الفجر", 30), ("البلد", 20),
          ("الشمس", 15), ("الليل", 21), ("الضحى", 11), ("الشرح", 8), ("التين", 8), ("العلق", 19), ("القدر", 5), ("البينة", 8), ("الزلزلة", 8), ("العاديات", 11),
          ("القارعة", 11), ("التكاثر", 8), ("العصر", 3), ("الهمزة", 9), ("الفيل", 5), ("قريش", 4), ("الماعون", 7), ("الكوثر", 3), ("الكافرون", 6), ("النصر", 3),
          ("المسد", 5), ("الإخلاص", 4), ("الفلق", 5), ("الناس", 6)]
QURAN_AYAT = sum(a for _, a in SURAHS)  # 6236
SUR_OFF = [sum(a for _, a in SURAHS[:i]) for i in range(114)]
HIZB_START = [(1, 1), (2, 75), (2, 142), (2, 203), (2, 253), (3, 15), (3, 93), (3, 171), (4, 24), (4, 88), (4, 148), (5, 27), (5, 82), (6, 36), (6, 111),
              (7, 1), (7, 88), (7, 171), (8, 41), (9, 34), (9, 93), (10, 26), (11, 6), (11, 84), (12, 53), (13, 19), (15, 1), (16, 51), (17, 1), (17, 99),
              (18, 75), (20, 1), (21, 1), (22, 1), (23, 1), (24, 21), (25, 21), (26, 111), (27, 56), (28, 51), (29, 46), (31, 22), (33, 31), (34, 24),
              (36, 28), (37, 145), (39, 32), (40, 41), (41, 47), (43, 24), (46, 1), (48, 18), (51, 31), (55, 1), (58, 1), (62, 1), (67, 1), (72, 1),
              (78, 1), (87, 1)]  # بداية كل حزب من الأحزاب الستين (مصحف المدينة)
_HZ = [SUR_OFF[sn - 1] + a for sn, a in HIZB_START] + [QURAN_AYAT + 1]


def done_hizbs(memo):
    """أرقام الأحزاب التي حُفظت كاملة من أول آية فيها إلى آخرها، من خريطة المحفوظ {سورة: {آيات}}."""
    got = {SUR_OFF[sn - 1] + a for sn, ays in memo.items() for a in ays}
    return [h + 1 for h in range(60) if all(i in got for i in range(_HZ[h], _HZ[h + 1]))]


def hizb_label(h):
    (s1, a1), e = HIZB_START[h - 1], _HZ[h] - 1
    s2 = max(i for i in range(114) if SUR_OFF[i] < e) + 1
    return f"الحزب {h} (من {SURAHS[s1 - 1][0]} {a1} إلى {SURAHS[s2 - 1][0]} {e - SUR_OFF[s2 - 1]})"


def holidays():
    return {d.strip() for d in cfg_get("holidays", "").split(",") if d.strip()}


def class_day(day_iso, hol=None):
    """هل هو يوم حلقة؟ (ليس الاثنين/الخميس/الجمعة ولا عطلة مسجَّلة)."""
    try:
        wd = dt.date.fromisoformat(day_iso).weekday()
    except ValueError:
        return False
    return wd in CLASS_WD and day_iso not in (holidays() if hol is None else hol)


def prev_month(m):
    y, mm = (int(x) for x in m.split("-"))
    return (dt.date(y, mm, 1) - dt.timedelta(days=1)).strftime("%Y-%m")



def is_new(l):
    """تسجيل حفظ يُحتسب في التقدم: مقطع جديد فقط (لا تكرار ولا إعادة قديمة ولا «لم يحفظ»)."""
    return l.get("type") == "hifz" and l.get("kind", "") in ("", "new") and l.get("grade") != "لم يحفظ"


def aya_set(l):
    """مجموعة (سورة، آية) التي يغطيها تسجيل مرتبط بسورة (أو بمدى من سورة إلى سورة)، وإلا مجموعة فارغة."""
    try:
        sn, a1, a2 = int(l.get("sur") or 0), int(l.get("a1") or 0), int(l.get("a2") or 0)
        s2 = int(l.get("sur2") or 0)
    except ValueError:
        return set()
    if s2 and s2 != sn:
        if not (1 <= sn <= 114 and 1 <= s2 <= 114) or not (1 <= a1 <= SURAHS[sn - 1][1]) or not (1 <= a2 <= SURAHS[s2 - 1][1]):
            return set()
        return {(g, k) for g, x1, x2 in segments(sn, a1, s2, a2) for k in range(x1, x2 + 1)}
    if not (1 <= sn <= 114) or not (1 <= a1 <= a2 <= SURAHS[sn - 1][1]):
        return set()
    return {(sn, k) for k in range(a1, a2 + 1)}


def memo_of(hifz_logs):
    out = {}
    for l in hifz_logs:
        if not is_new(l):
            continue
        for sn, k in aya_set(l):
            out.setdefault(sn, set()).add(k)
    return out


def memo_full(hifz_logs):
    """المحفوظ الفعلي: يبدأ الطالب بالفاتحة ثم يحفظ من الناس صعودا، فكل سورة بين الناس وأدنى سورة (غير الفاتحة) سُجّل فيها حفظ جديد تُعدّ محفوظة كاملة."""
    m = memo_of(hifz_logs)
    rest = [sn for sn in m if sn != 1]  # الطالب الجديد يبدأ بالفاتحة ثم ينتقل إلى الناس، فلا تُعدّ الفاتحة بداية الصعود
    if rest:
        for sn in range(min(rest) + 1, 115):
            m[sn] = set(range(1, SURAHS[sn - 1][1] + 1))
    return m


def to_ranges(aset):
    """يحوّل مجموعة (سورة، آية) إلى مقاطع متصلة [(سورة، من، إلى)]."""
    out = []
    for sn in sorted({a for a, _ in aset}):
        ks = sorted(k for a, k in aset if a == sn)
        a1 = prev = ks[0]
        for k in ks[1:]:
            if k != prev + 1:
                out.append((sn, a1, prev))
                a1 = k
            prev = k
        out.append((sn, a1, prev))
    return out


def range_label(r):
    sn, a1, a2 = r
    return f"سورة {SURAHS[sn - 1][0]} " + (f"الآية {a1}" if a1 == a2 else f"من الآية {a1} إلى الآية {a2}")


def segments(s1, a1, s2, a2):
    """مقاطع تسجيل يمتد من (سورة، آية) إلى (سورة، آية): السورة الأولى من آيتها إلى آخرها، فما بينهما كاملة، والأخيرة من أولها إلى آيتها."""
    if s1 == s2:
        return [(s1, a1, a2)]
    step = 1 if s2 > s1 else -1
    return [(s1, a1, SURAHS[s1 - 1][1])] + [(k, 1, SURAHS[k - 1][1]) for k in range(s1 + step, s2, step)] + [(s2, 1, a2)]


def seg_text(segs, pre=""):
    if len(segs) == 1:
        sn, a1, a2 = segs[0]
        return f"{pre}سورة {SURAHS[sn - 1][0]} من الآية {a1} إلى الآية {a2}"
    (s1, a1, _), (s2, _, a2) = segs[0], segs[-1]
    return f"{pre}من سورة {SURAHS[s1 - 1][0]} الآية {a1} إلى سورة {SURAHS[s2 - 1][0]} الآية {a2}"


REV_DAYS = 14


def _ago(day, n):
    return (dt.date.fromisoformat(day) - dt.timedelta(days=n)).isoformat()


def recent_hifz(sid, logs, day, days=REV_DAYS):
    """ما حفظه الطالب في آخر أسبوعين ولم تُسجَّل مراجعته بعد (مرتبا من الأحدث)."""
    cut = _ago(day, days)
    mine_ = [l for l in logs if l["sid"] == sid and l["date"] <= day]
    new = {}
    for l in mine_:
        if is_new(l) and l["date"] >= cut:
            for a in aya_set(l):
                new[a] = max(new.get(a, ""), l["date"])
    for l in mine_:
        if l["type"] != "hifz":
            for a in aya_set(l):
                if a in new and l["date"] >= new[a]:
                    del new[a]
    return sorted(to_ranges(set(new)), key=lambda r: max(new[(r[0], k)] for k in range(r[1], r[2] + 1)), reverse=True)


def stale_ranges(sid, logs, day, days=REV_DAYS):
    """محفوظ لم يُراجَع (ولم يُحفَظ) منذ أكثر من أسبوعين، مرتبا من الأقدم، مع نسبة المراجَع حديثا."""
    cut = _ago(day, days)
    seen = {}
    for l in logs:
        if l["sid"] == sid and l["date"] <= day:
            for a in aya_set(l):
                seen[a] = max(seen.get(a, ""), l["date"])
    memo = {a for l in logs if l["sid"] == sid and is_new(l) and l["date"] <= day for a in aya_set(l)}
    old = {a for a in memo if seen.get(a, "") < cut}
    rs = sorted(to_ranges(old), key=lambda r: min(seen[(r[0], k)] for k in range(r[1], r[2] + 1)))
    return rs, len(memo), len(memo) - len(old)


def review_status_html(sid, logs, day):
    rec = recent_hifz(sid, logs, day)
    rs, tot, fresh = stale_ranges(sid, logs, day)
    out = ""
    pk_ = review_pick([l for l in logs if l["sid"] == sid], day)
    if pk_:
        out += '<div class="pay no">اسمع له اليوم: ' + esc(review_pick_text(pk_)) + "</div>"
    if rec:
        out += '<div class="note">اقتراح المراجعة (حفظه في آخر أسبوعين): ' + " · ".join(esc(range_label(r)) for r in rec[:4]) + "</div>"
    if tot:
        pct = round(100 * fresh / tot)
        out += (f'<div class="pay {"ok" if pct >= 70 else "no"}">ختمة المحفوظ: روجع حديثا {fresh} من {tot} آية ({pct}%)</div>'
                f'<div class="bar"><i style="width:{max(pct, 1.5)}%"></i></div>')
        if rs:
            out += '<div class="note">لم يُراجَع منذ أكثر من أسبوعين: ' + " · ".join(esc(range_label(r)) for r in rs[:4]) + (f" … (+{len(rs) - 4})" if len(rs) > 4 else "") + "</div>"
    return out


def month_range_label(m):
    y, mm = (int(x) for x in m.split("-"))
    last = calendar.monthrange(y, mm)[1]
    return f"من 01 {MONTHS_AR[mm - 1]} {y} إلى {last:02d} {MONTHS_AR[mm - 1]} {y}"


def progress_html(hifz_logs):
    m = memo_full(hifz_logs)
    tot = sum(len(v) for v in m.values())
    if not tot:
        return '<div class="empty">لم يُسجَّل حفظ مرتبط بالسور بعد.</div>'
    pct = round(100 * tot / QURAN_AYAT, 1)
    chips = "".join(
        f'<span class="gr {"g1" if len(m[sn]) == SURAHS[sn - 1][1] else "g3"}" style="margin:3px 3px 0 0;display:inline-block">'
        f'{SURAHS[sn - 1][0]} {len(m[sn])}/{SURAHS[sn - 1][1]}'
        + ("" if len(m[sn]) == SURAHS[sn - 1][1] else f" · بقي {SURAHS[sn - 1][1] - len(m[sn])}")
        + "</span>"
        for sn in sorted(m, reverse=True)
    )
    done = sum(1 for sn in m if len(m[sn]) == SURAHS[sn - 1][1])
    return (f'<div class="pay ok">المحفوظ: {tot} آية من {QURAN_AYAT} ({pct:g}%) · سور مكتملة: {done}</div>'
            f'<div class="bar"><i style="width:{max(pct, 1.5)}%"></i></div><div>{chips}</div>')


def recent_months(n=8):
    d = dt.datetime.now(TZ).date().replace(day=1)
    out = []
    for _ in range(n):
        out.append(d.strftime("%Y-%m"))
        d = (d - dt.timedelta(days=1)).replace(day=1)
    return out


def month_label(m):
    y, mm = m.split("-")
    return f"{MONTHS_AR[int(mm) - 1]} {y}"


def num(x):
    try:
        return float(str(x).replace(",", ".").strip() or 0)
    except ValueError:
        return 0.0


def grade_name(avg):
    if avg is None:
        return "—"
    return "ممتاز" if avg >= 4.5 else "جيد جدا" if avg >= 3.5 else "جيد" if avg >= 2.5 else "متوسط" if avg >= 1.5 else "يحتاج إعادة"


def disc_label(v):
    return "لم يُقيَّم" if v is None else "منضبط" if v >= 2.5 else "متوسط" if v >= 1.5 else "غير منضبط"


HW = {"dis": 25, "att": 25, "mur": 20, "hif": 15, "hgr": 15}  # توزيع نقاط الترتيب من 100
HW_NAMES = {"dis": "الانضباط", "att": "الحضور وعدم الغياب", "mur": "تقدير المراجعة", "hif": "التقدم في الحفظ", "hgr": "تقدير الحفظ"}


def hifz_target():
    try:
        return max(1, int(float(cfg_get("hifz_target", "30"))))
    except ValueError:
        return 30


def month_stats(month, students, logs, att, disc, exams=None):
    """إحصاءات كل طالب في الشهر، والترتيب بمجموع النقاط (من 100)."""
    out = {}
    if isinstance(month, tuple):  # فترة (من، إلى) بدل شهر كامل، مثل أسبوع
        lo, hi = month
        span = (dt.date.fromisoformat(hi) - dt.date.fromisoformat(lo)).days + 1
    else:
        lo, hi, span = month + "-01", month + "-31", 30
    inm = lambda d: lo <= d <= hi
    target = hifz_target()
    hol = holidays()
    exams = exams or []
    exam_rank = cfg_get("exam_rank") == "1"
    held = len({a_["date"] for a_ in att if inm(a_["date"]) and class_day(a_["date"], hol)})  # حصص الشهر الفعلية فقط
    for s in students:
        sid = s["id"]
        L = [l for l in logs if l["sid"] == sid and inm(l["date"])]
        hl = [l for l in L if l["type"] == "hifz"]
        ml = [l for l in L if l["type"] != "hifz"]
        A = [a for a in att if a["sid"] == sid and inm(a["date"]) and class_day(a["date"], hol)]
        dv = [int(d["score"]) for d in disc if d["sid"] == sid and inm(d["date"]) and d["score"] in ("1", "2", "3")]
        p, lt, ab, ex = (sum(a["status"] == k for a in A) for k in ("p", "l", "a", "e"))
        denom = max(held - ex, 0)  # الغياب بعذر لا يُحسب عليه
        tot = held
        pct = round(100 * min(p + LATE_W * lt, denom) / denom, 1) if denom else None
        dis = round(sum(dv) / len(dv), 2) if dv else None

        def gp(ls):
            v = [GPTS[l["grade"]] for l in ls if l["grade"] in GPTS]
            return round(sum(v) / len(v), 2) if v else None

        qty = round(sum(num(l.get("qty")) for l in hl), 1)
        hln = [l for l in hl if is_new(l)]  # الجديد فقط يُحتسب في التقدم
        aya = len(set().union(*[aya_set(l) for l in hln])) if hln else 0
        tot_aya = sum(len(v_) for v_ in memo_full([l for l in logs if l["sid"] == sid and l["date"] <= hi]).values())  # الإجمالي يشمل ما قبل أدنى سورة سُجّلت
        mur = gp(ml)
        hg = gp(hl)
        tgt = max(1, round((int(num(s.get("target"))) or target) * span / 30))
        prog = min(1.0, aya / tgt) if aya else min(1.0, len(hln) / 8)  # تسجيل بلا سورة: نحسب عدد الحصص (8 حصص = كامل)
        pts = {"dis": (dis or 0) / 3 * HW["dis"], "att": (pct or 0) / 100 * HW["att"], "mur": (mur or 0) / 5 * HW["mur"],
               "hif": prog * HW["hif"], "hgr": (hg or 0) / 5 * HW["hgr"]}
        score = round(sum(pts.values()), 1)
        EX = [e for e in exams if e["sid"] == sid and inm(e["date"])]
        ex_avg = round(sum(num(e["score"]) for e in EX) / len(EX), 2) if EX else None
        exam_on = bool(exam_rank and ex_avg is not None)
        if exam_on:  # الاختبار يعطي 10% من المجموع، ومن لا اختبار له يبقى مجموعه كما هو
            score = round(score * 0.9 + min(ex_avg, 20) / 20 * 10, 1)
        out[sid] = {
            "pts": pts, "score": score,
            "hl": sorted(hl, key=lambda x: x["date"]), "ml": sorted(ml, key=lambda x: x["date"]),
            "present": p + lt, "late": lt, "exam": ex_avg, "exam_n": len(EX), "exam_on": exam_on, "target": tgt, "absent": ab, "excused": ex, "total": tot, "pct": pct,
            "abs_dates": sorted(a["date"] for a in A if a["status"] == "a"),
            "exc_dates": sorted(a["date"] for a in A if a["status"] == "e"),
            "dis": dis, "dn": len(dv), "mur": mur, "hif": gp(hl), "qty": qty, "aya": aya, "tot_aya": tot_aya,
            "has": bool(L or A or dv),
            "key": (score, pct or 0, dis or 0, aya, qty, len(hl)),
        }
    return out


def challenge_status(stu, month, logs, att, disc):
    """تحدي الشهر: أربعة أهداف، لكل منها حالة: ok محقق حتى الآن، bad انكسر، none لم يبدأ بعد."""
    sid = stu["id"]
    hol = holidays()
    today_ = now().date().isoformat()
    A = [a for a in att if a["sid"] == sid and a["date"][:7] == month and class_day(a["date"], hol)]
    out = []
    ab = sum(a["status"] == "a" for a in A)
    out.append(("صفر غياب", "bad" if ab else ("ok" if A else "none")))
    dv = [d["score"] for d in disc if d["sid"] == sid and d["date"][:7] == month and d["score"] in ("1", "2", "3")]
    out.append(("انضباط كامل", "none" if not dv else "ok" if all(v == "3" for v in dv) else "bad"))
    ml = [l for l in logs if l["sid"] == sid and l["type"] != "hifz" and l["date"][:7] == month]
    out.append(("مراجعة ممتازة بلا أخطاء", "none" if not ml else "ok" if all(l["grade"] == "ممتاز" and not (l.get("note") or "").strip() for l in ml) else "bad"))
    hl = [l for l in logs if l["sid"] == sid and l["type"] == "hifz" and l["date"][:7] == month]
    wds = {DAYS[k][1] for k in days_of(stu)}
    dates = {l["date"] for l in hl}
    dates |= {a["date"] for a in A if a["status"] in ("p", "l") and a["date"] < today_ and dt.date.fromisoformat(a["date"]).weekday() in wds}
    newd = {l["date"] for l in hl if is_new(l)}
    out.append(("حفظ جديد في كل حصة حفظ", "none" if not dates else "ok" if dates <= newd else "bad"))
    return out


def challenge_html(stu, month, logs, att, disc):
    st_ = challenge_status(stu, month, logs, att, disc)
    ok = sum(1 for _, v in st_ if v == "ok")
    broken = sum(1 for _, v in st_ if v == "bad")
    chips = "".join(f'<span class="ci {v}">{"✓ " if v == "ok" else "✗ " if v == "bad" else ""}{esc(t)}</span>' for t, v in st_)
    msg = ("أحسنتم! لا يزال التحدي كاملا حتى الآن، فاستمروا." if ok and not broken else
           "انكسر بعض الأهداف هذا الشهر، وسيبدأ تحدٍّ جديد في الشهر القادم بإذن الله." if broken else "ابدؤوا الشهر بقوة، وحافظوا على الأهداف الأربعة.")
    return (f'<div class="chal"><div class="ct">🎯 تحدي شهر {esc(month_label(month))}<small>{ok} من 4 محقق حتى الآن</small></div>'
            f'<div class="cl">{chips}</div><div class="cm">{msg}</div></div>')


def _ranks(S):
    ranked = [k for k, v in S.items() if v["has"]]
    return {k: 1 + sum(1 for j in ranked if S[j]["key"] > S[k]["key"]) for k in ranked}


def _badges(sid, month, v, rk, rP, rP2, logs, ch=None):
    out = []
    if ch and month < now().strftime("%Y-%m") and all(x == "ok" for _, x in ch):
        out.append(("🏆", "أتمّ تحدي الشهر كاملا"))
    if v["total"] >= 2 and v["pct"] == 100:
        out.append(("🏅", "حضور كامل هذا الشهر"))
    if v["dis"] is not None and v["dn"] >= 2 and v["dis"] >= 2.8:
        out.append(("🌟", "انضباط ممتاز هذا الشهر"))
    hl = [l for l in logs if l["sid"] == sid and is_new(l)]
    before = memo_of([l for l in hl if l["date"][:7] < month])
    upto = memo_of([l for l in hl if l["date"][:7] <= month])
    full = lambda m: {sn for sn, a in m.items() if len(a) == SURAHS[sn - 1][1]}
    newfull = sorted(full(upto) - full(before), reverse=True)
    if len(newfull) > 4:
        out.append(("📖", f"أتمّ حفظ {len(newfull)} سورة هذا الشهر (من {SURAHS[newfull[0] - 1][0]} إلى {SURAHS[newfull[-1] - 1][0]})"))
    else:
        for sn in newfull:
            out.append(("📖", f"أتمّ حفظ سورة {SURAHS[sn - 1][0]}"))
    hb = set(done_hizbs(before))
    for h in done_hizbs(upto):
        if h not in hb:
            out.append(("🎓", f"أتمّ حفظ الحزب {h}"))
    if rk.get(sid, 99) <= 3 and rP.get(sid, 99) <= 3 and rP2.get(sid, 99) <= 3:
        out.append(("🥇", "ثلاثة أشهر متتالية في الأوائل"))
    return out


def month_bundle(month):
    students, logs, att, disc, exams = (load(n) for n in ("students", "logs", "att", "disc", "exams"))
    S = month_stats(month, students, logs, att, disc, exams)
    rank = _ranks(S)
    pm = prev_month(month)
    P = month_stats(pm, students, logs, att, disc, exams)
    rP = _ranks(P)
    rP2 = _ranks(month_stats(prev_month(pm), students, logs, att, disc, exams))
    smap = {x["id"]: x for x in students}
    for sid, v in S.items():
        v["prev"] = P[sid] if P[sid]["has"] else None
        v["badges"] = _badges(sid, month, v, rank, rP, rP2, logs, challenge_status(smap[sid], month, logs, att, disc))
    return S, rank, len(rank)


def _has_ar(t):
    return any("؀" <= ch <= "ۿ" for ch in t)


def _shape(t):
    import arabic_reshaper
    from bidi.algorithm import get_display
    return get_display(arabic_reshaper.reshape(t)) if _has_ar(t) else t


FRESH_CUTS = (7, 14, 30)  # أيام: أخضر داكن ≤7، أخضر ≤14، كهرماني ≤30، أحمر بعد ذلك


def surah_fresh(logs_all, day=None):
    """لكل سورة محفوظة: أقدم مراجعة لآياتها المحفوظة. age=None يعني آيات لا تسجيل لها (عُدّت محفوظة تلقائيا)."""
    day = day or today()
    m = memo_full([l for l in logs_all if l["type"] == "hifz"])
    seen = {}
    for l in logs_all:
        if l["date"] <= day:
            for a in aya_set(l):
                if l["date"] > seen.get(a, ""):
                    seen[a] = l["date"]
    d0 = dt.date.fromisoformat(day)
    out = {}
    for sn, ks in m.items():
        ages = [(d0 - dt.date.fromisoformat(seen[(sn, k)])).days for k in ks if (sn, k) in seen]
        unk = len(ks) - len(ages)
        out[sn] = {"age": max(ages) if ages else None, "unknown": unk > 0, "n": len(ks), "fresh": sum(1 for a_ in ages if a_ <= FRESH_CUTS[1])}
    return out


def fresh_class(f):
    if f is None or f["unknown"]:
        return "f4"
    a = f["age"]
    return "f0" if a <= FRESH_CUTS[0] else "f1" if a <= FRESH_CUTS[1] else "f2" if a <= FRESH_CUTS[2] else "f3"


def review_pick(logs_all, day=None, n=3):
    """اقتراح «اسمع له اليوم»: الأقدم مراجعةً أولا، ثم سور بلا مراجعة مسجّلة. [(سورة، أيام أو None)]"""
    fr = surah_fresh(logs_all, day)
    stale = sorted([(f["age"], sn) for sn, f in fr.items() if not f["unknown"] and f["age"] > FRESH_CUTS[1]], reverse=True)
    out = [(sn, a) for a, sn in stale[:n]]
    if len(out) < n:
        unk = sorted([sn for sn, f in fr.items() if f["unknown"]], reverse=True)
        out += [(sn, None) for sn in unk[: n - len(out)]]
    return out


def review_pick_text(pick):
    return " · ".join(f"سورة {SURAHS[sn - 1][0]} (" + (f"مضى {a} يوما على آخر مراجعة" if a is not None else "لا مراجعة مسجّلة") + ")" for sn, a in pick)


def quran_map_html(logs_all, day=None):
    """خريطة حيّة: تبهت السورة المحفوظة كلما طال الزمن على آخر مراجعة لها. تأخذ كل تسجيلات الطالب (حفظ ومراجعة)."""
    m = memo_full([l for l in logs_all if l["type"] == "hifz"])
    fr = surah_fresh(logs_all, day)
    cells = []
    full = 0
    for sn in range(1, 115):
        n, tot = len(m.get(sn, ())), SURAHS[sn - 1][1]
        full += n == tot
        if n:
            f = fr[sn]
            when = "لا مراجعة مسجّلة" if f["age"] is None else f"أقدم مراجعة قبل {f['age']} يوما" + (" (وجزء بلا تسجيل)" if f["unknown"] else "")
            cells.append(f'<span class="mc {"mfull" if n == tot else "mpart"} {fresh_class(f)}" title="{esc(SURAHS[sn - 1][0])}: {n} من {tot} · {when}">{sn}</span>')
        else:
            cells.append(f'<span class="mc mnone" title="{esc(SURAHS[sn - 1][0])}: {n} من {tot}">{sn}</span>')
    lg = lambda c, t: f'<span class="lg-f mc {c}"></span>{t}'
    return (f'<div class="qmap">{"".join(cells)}</div>'
            f'<div class="meta" style="font-size:.8rem;color:var(--mut)">'
            f'{lg("f0", "روجعت خلال أسبوع")} · {lg("f1", "خلال أسبوعين")} · {lg("f2", "خلال شهر")} · {lg("f3", "مضى أكثر من شهر")} · {lg("f4", "لا مراجعة مسجّلة")} · '
            f'<span class="lg-f mc mnone"></span>لم تُحفظ بعد — السور المحفوظة كاملة: {full}. الإطار المتقطع: سورة قيد الحفظ. '
            f'يُعدّ محفوظا كل ما بين سورة الناس والسورة التي وصل إليها.</div>')


def compare_items(v):
    P = v.get("prev")
    if not P:
        return []
    spec = [("المجموع", "score", "{:g}"), ("الانضباط", "dis", "{:.2f}"), ("الحضور %", "pct", "{:g}"), ("تقدير المراجعة", "mur", "{:.2f}"), ("آيات الشهر", "aya", "{:g}")]
    out = []
    for lab, k, f in spec:
        a, b = v.get(k), P.get(k)
        if a is None or b is None:
            continue
        d = a - b
        out.append({"lab": lab, "now": f.format(a), "prev": f.format(b), "dir": 1 if d > 0.004 else -1 if d < -0.004 else 0, "diff": f.format(abs(d))})
    return out


def month_ending(mo, last_days=7):
    """المقارنة تظهر للولي في آخر أيام الشهر (أو بعد انتهائه) وليس في بدايته."""
    t = today()
    if mo < t[:7]:
        return True
    if mo > t[:7]:
        return False
    y, m = int(mo[:4]), int(mo[5:7])
    last = ((dt.date(y + (m == 12), m % 12 + 1, 1)) - dt.timedelta(days=1)).day
    return int(t[8:10]) > last - last_days


def compare_html(v):
    its = compare_items(v)
    if not its:
        return ""
    rows = []
    for it in its:
        word = {1: f"▲ ارتفع {it['diff']}", -1: f"▼ انخفض {it['diff']}", 0: "= ثابت"}[it["dir"]]
        col = {1: "#2e7d32", -1: "#b3261e", 0: "#6b7a72"}[it["dir"]]
        rows.append(f'<div class="meta" style="margin:3px 0"><b>{it["lab"]}:</b> {it["now"]} <span style="color:{col}">{word}</span> <span>(الشهر السابق {it["prev"]})</span></div>')
    return '<div class="note"><b>مقارنة بالشهر السابق</b>' + "".join(rows) + "</div>"


EXAM_KINDS = ["اختبار حزب", "اختبار شهري", "اختبار آخر"]


def exams_html(sid):
    E = sorted([e for e in load("exams") if e["sid"] == sid], key=lambda e: e["date"], reverse=True)
    if not E:
        return '<div class="empty">لا توجد اختبارات مسجَّلة بعد.</div>'
    out = []
    for e in E[:15]:
        sc = num(e["score"])
        title_ = e["kind"] + (f" — الحزب {e['part']}" if e["kind"] == "اختبار حزب" and e["part"] else "")
        out.append(f'<div class="ent"><i class="med"></i><div class="bd2"><div class="txt">{esc(title_)}</div>'
                   f'<div class="meta"><span>{esc(e["date"])}</span><span>{esc(e["teacher"])}</span>' + (f'<span>{esc(e["note"])}</span>' if e["note"] else "") +
                   f'</div></div><span class="gr {"g1" if sc >= 16 else "g3" if sc >= 10 else "g5"}">{sc:g} / 20</span></div>')
    return "".join(out)


def hizb_candidates(sid, logs, exams):
    """أحزاب أتمّ الطالب حفظها كاملة ولم يُسجَّل له اختبار فيها."""
    done = done_hizbs(memo_full([l for l in logs if l["sid"] == sid and l["type"] == "hifz"]))
    tested = {int(e["part"]) for e in exams if e["sid"] == sid and e["kind"] == "اختبار حزب" and str(e["part"]).isdigit()}
    return [h for h in done if h not in tested]


def need_follow(students, day):
    att, disc, logs = load("att"), load("disc"), load("logs")
    hol = holidays()
    held = sorted({a["date"] for a in att if a["date"] <= day and class_day(a["date"], hol)})[-2:]
    cutoff = _ago(day, 14)
    out = []
    for x in students:
        sid, why = x["id"], []
        if len(held) == 2:
            stt = {a["date"]: a["status"] for a in att if a["sid"] == sid and a["date"] in held}
            if all(stt.get(d_) == "a" for d_ in held):
                why.append(f"غاب آخر حصتين ({held[0][5:]} و{held[1][5:]})")
        news = [l["date"] for l in logs if l["sid"] == sid and is_new(l)]
        if not news:
            why.append("لا حفظ جديد مسجَّل بعد")
        elif max(news) < cutoff:
            why.append(f"لا حفظ جديد منذ {(dt.date.fromisoformat(day) - dt.date.fromisoformat(max(news))).days} يوما")
        ds = sorted([d_ for d_ in disc if d_["sid"] == sid and d_["score"] in ("1", "2", "3") and d_["date"] <= day], key=lambda d_: d_["date"])[-4:]
        if len(ds) >= 2:
            avg = sum(int(d_["score"]) for d_ in ds) / len(ds)
            if avg < 2.0:
                why.append(f"الانضباط ضعيف (معدل آخر {len(ds)} تقييمات: {avg:.1f} من 3)")
        if why:
            out.append((x, why))
    return out


def student_pdf(stu, month, bundle):
    """يبني تقرير PDF لطالب واحد ويعيد bytes."""
    from reportlab.lib.colors import HexColor, white
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfgen import canvas

    if not os.path.exists(FONT):
        raise RuntimeError("ملف الخط Amiri-Regular.ttf غير موجود في GitHub بجانب app.py")
    if "Amiri" not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont("Amiri", FONT))
    S, rank, total = bundle
    v = S[stu["id"]]
    INK, GOLD, PAPER, LINE, MUT = HexColor("#0a4a3e"), HexColor("#a9822a"), HexColor("#f3f5ee"), HexColor("#d6ddcb"), HexColor("#5f6f67")
    W, H = A4
    L, R = 36, W - 36
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    c.setTitle(f"تقرير {stu['name']} - {month_label(month)}")
    st_ = {"y": 0, "page": 1}

    def put(x, y, t, size=12, align="r", color=INK):
        c.setFont("Amiri", size)
        c.setFillColor(color)
        t = _shape(str(t))
        {"r": c.drawRightString, "l": c.drawString, "c": c.drawCentredString}[align](x, y, t)

    def wrap(t, size, maxw):
        words, lines, cur = str(t).split(), [], ""
        for w in words:
            nt = (cur + " " + w).strip()
            if c.stringWidth(_shape(nt), "Amiri", size) <= maxw:
                cur = nt
            else:
                if cur:
                    lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)
        return lines or [""]

    def footer():
        c.setStrokeColor(LINE)
        c.line(L, 44, R, 44)
        put(W / 2, 28, f"{ASSOC} – {SEC}", 10, "c", MUT)
        put(L, 28, str(st_["page"]), 10, "l", MUT)

    def big_header():
        c.setFillColor(INK)
        c.rect(0, H - 100, W, 100, stroke=0, fill=1)
        c.setFillColor(GOLD)
        c.rect(0, H - 104, W, 4, stroke=0, fill=1)
        lp = os.path.join(HERE, "logo.jpg")
        if os.path.exists(lp):
            c.setFillColor(white)
            c.roundRect(L, H - 90, 74, 74, 10, stroke=0, fill=1)
            c.drawImage(lp, L + 4, H - 86, 66, 66, preserveAspectRatio=True, mask="auto")
        put(R, H - 48, ASSOC, 24, "r", white)
        put(R, H - 74, f"{SEC}  ·  التقرير الشهري للطالب", 14, "r", HexColor("#e8d9a0"))
        st_["y"] = H - 104

    def small_header():
        c.setFillColor(INK)
        c.rect(0, H - 40, W, 40, stroke=0, fill=1)
        c.setFillColor(GOLD)
        c.rect(0, H - 43, W, 3, stroke=0, fill=1)
        put(R, H - 26, f"{stu['name']}  ·  {month_label(month)}", 13, "r", white)
        st_["y"] = H - 43

    def need(h):
        if st_["y"] - h < 60:
            footer()
            c.showPage()
            st_["page"] += 1
            small_header()
            st_["y"] -= 22

    def title(t):
        need(46)
        st_["y"] -= 26
        put(R, st_["y"], t, 16, "r", INK)
        c.setStrokeColor(GOLD)
        c.setLineWidth(1.2)
        c.line(L, st_["y"] - 7, R, st_["y"] - 7)
        c.setLineWidth(1)
        st_["y"] -= 14

    def table(cols, rows, empty):
        # cols: [(عنوان، عرض)] من اليمين إلى اليسار، والعمود الثاني مرن
        fixed = sum(w for _, w in cols if w)
        widths = [w or (R - L - fixed) for _, w in cols]
        need(24)
        y = st_["y"] - 20
        c.setFillColor(INK)
        c.rect(L, y, R - L, 20, stroke=0, fill=1)
        x = R
        for (h_, _), w in zip(cols, widths):
            put(x - 6, y + 6, h_, 11, "r", white)
            x -= w
        st_["y"] = y
        if not rows:
            need(26)
            st_["y"] -= 24
            put(R - 6, st_["y"] + 6, empty, 11, "r", MUT)
            return
        for k, row in enumerate(rows):
            cells = [wrap(t, 12, w - 12) if i == 1 else [str(t)] for i, (t, w) in enumerate(zip(row, widths))]
            rh = max(len(x_) for x_ in cells) * 15 + 7
            need(rh)
            y = st_["y"] - rh
            if k % 2 == 0:
                c.setFillColor(PAPER)
                c.rect(L, y, R - L, rh, stroke=0, fill=1)
            x = R
            for ci, (lines, w) in enumerate(zip(cells, widths)):
                for li, ln in enumerate(lines):
                    put(x - 6, y + rh - 16 - li * 15, ln, 12, "r", INK)
                x -= w
            st_["y"] = y
        c.setStrokeColor(LINE)
        c.line(L, st_["y"], R, st_["y"])

    big_header()
    st_["y"] -= 40
    put(W / 2, st_["y"], stu["name"], 28, "c", INK)
    st_["y"] -= 26
    put(W / 2, st_["y"], f"تقييم شهر {month_label(month)}", 15, "c", GOLD)
    st_["y"] -= 17
    put(W / 2, st_["y"], month_range_label(month), 11, "c", MUT)
    st_["y"] -= 16

    # بطاقات ملخصة
    bw, gap, bh = (R - L - 20) / 3, 10, 74
    y0 = st_["y"] - bh
    r_ = rank.get(stu["id"])
    cards = [
        ("الانضباط", f"{v['dis']:.2f} / 3" if v["dis"] is not None else "—", disc_label(v["dis"])),
        ("الحضور", f"{v['pct']:g}%" if v["pct"] is not None else "—", f"حضر {v['present']} من {v['total']} حصة" if v["total"] else "لا يوجد تسجيل"),
        ("الترتيب في الحلقة", f"{r_} من {total}" if r_ else "—", f"{v['score']:g} نقطة من 100"),
    ]
    for k, (lab, val, sub) in enumerate(cards):
        x1 = R - k * (bw + gap)
        c.setFillColor(HexColor("#fbfcf8"))
        c.setStrokeColor(LINE)
        c.roundRect(x1 - bw, y0, bw, bh, 8, stroke=1, fill=1)
        c.setFillColor(GOLD)
        c.rect(x1 - bw + 10, y0 + bh - 3, bw - 20, 3, stroke=0, fill=1)
        put(x1 - bw / 2, y0 + bh - 20, lab, 12, "c", MUT)
        put(x1 - bw / 2, y0 + 30, val, 22, "c", INK)
        put(x1 - bw / 2, y0 + 11, sub, 9.5, "c", MUT)
    st_["y"] = y0

    title("تفصيل نقاط الترتيب")
    for k in HW:
        need(20)
        st_["y"] -= 18
        put(R, st_["y"], HW_NAMES[k], 12, "r", INK)
        put(R - 230, st_["y"], f"{v['pts'][k]:.1f} من {HW[k]}", 12, "r", INK)
    need(24)
    st_["y"] -= 22
    put(R, st_["y"], "المجموع", 13, "r", GOLD)
    put(R - 230, st_["y"], f"{v['score']:g} من 100", 13, "r", GOLD)
    if v.get("exam_on"):
        st_["y"] -= 16
        put(R, st_["y"], f"محسوبة مع الاختبارات (معدل الاختبارات {v['exam']:g} من 20 = 10% من المجموع)", 10.5, "r", MUT)
    if v.get("badges"):
        title("الأوسمة")
        for _ic, tx in v["badges"]:
            need(18)
            st_["y"] -= 17
            put(R, st_["y"], "- وسام: " + tx, 12, "r", GOLD)
    cmp_ = compare_items(v) if month_ending(month) else []
    if cmp_:
        title("مقارنة بالشهر السابق")
        for it in cmp_:
            need(18)
            st_["y"] -= 17
            wd_ = {1: f"ارتفع {it['diff']}", -1: f"انخفض {it['diff']}", 0: "ثابت"}[it["dir"]]
            put(R, st_["y"], f"{it['lab']}: {it['now']}  ({wd_} عن الشهر السابق {it['prev']})", 12, "r", INK)
    title("الحضور والغياب")
    st_["y"] -= 14
    put(R, st_["y"], f"أيام الحضور: {v['present']}" + (f" (منها {v['late']} متأخر)" if v.get("late") else "") + f"      الغياب: {v['absent']}      الغياب بعذر: {v['excused']}      نسبة الحضور: " + (f"{v['pct']:g}%" if v["pct"] is not None else "—"), 13, "r", INK)
    for lab, ds in (("تواريخ الغياب", v["abs_dates"]), ("تواريخ الغياب بعذر", v["exc_dates"])):
        if ds:
            for ln in wrap(lab + ": " + "  ،  ".join(d[8:10] + "/" + d[5:7] for d in ds), 11, R - L):
                need(18)
                st_["y"] -= 18
                put(R, st_["y"], ln, 11, "r", MUT)

    title("الحفظ")
    cols = [("التاريخ", 78), ("المقدار المحفوظ", None), ("التقدير", 80), ("الآيات", 54)]
    table(cols, [(l["date"], (f"[{KIND_TAG[l['kind']]}] " if l.get("kind") in KIND_TAG and l.get("kind") != "none" else "") + l["detail"] + (f"  ({l['note']})" if l["note"] else ""), l["grade"] or "—", (str(len(aya_set(l))) if aya_set(l) and is_new(l) else "—")) for l in v["hl"]], "لا يوجد حفظ مسجَّل في هذا الشهر")
    st_["y"] -= 18
    need(20)
    put(R, st_["y"], f"عدد حصص الحفظ: {len(v['hl'])}" + (f"      آيات الشهر: {v['aya']}" if v["aya"] else "") + (f"      التقييم العام للحفظ: {grade_name(v['hif'])}" if v["hif"] else ""), 12, "r", INK)

    if v["tot_aya"]:
        st_["y"] -= 18
        need(20)
        put(R, st_["y"], f"إجمالي ما حفظه من القرآن: {v['tot_aya']} آية من {QURAN_AYAT}، أي {round(100 * v['tot_aya'] / QURAN_AYAT, 1):g} بالمئة", 12, "r", GOLD)

    title("خريطة الحفظ")
    memo_ = memo_full([l for l in load("logs") if l["sid"] == stu["id"] and l["date"][:7] <= month])
    ncol, cw_, chh = 19, (R - L) / 19, 21
    need(6 * chh + 34)
    top_ = st_["y"] - 8
    for k_ in range(114):
        r_i, c_i = divmod(k_, ncol)
        x1_, y1_ = R - (c_i + 1) * cw_ + 2, top_ - (r_i + 1) * chh + 2
        n_, tot_ = len(memo_.get(k_ + 1, ())), SURAHS[k_][1]
        c.setFillColor(INK if n_ == tot_ else HexColor("#e3c869") if n_ else HexColor("#e6eadf"))
        c.roundRect(x1_, y1_, cw_ - 4, chh - 4, 3, stroke=0, fill=1)
        put(x1_ + (cw_ - 4) / 2, y1_ + 5.5, str(k_ + 1), 8.5, "c", white if n_ == tot_ else INK if n_ else MUT)
    st_["y"] = top_ - 6 * chh - 6
    put(R, st_["y"], "أخضر داكن: سورة محفوظة كاملة   ·   ذهبي: قيد الحفظ   ·   رمادي: لم تبدأ", 10, "r", MUT)
    title("المراجعة")
    cols_m = [("التاريخ", 78), ("ما تمت مراجعته", None), ("التقدير", 80)]
    table(cols_m, [(l["date"], l["detail"] + (f"  — يعيد: {l['note']}" if l["note"] else ""), l["grade"] or "—") for l in v["ml"]], "لا توجد مراجعة مسجَّلة في هذا الشهر")
    st_["y"] -= 18
    need(20)
    put(R, st_["y"], f"عدد حصص المراجعة: {len(v['ml'])}" + (f"      التقييم العام للمراجعة: {grade_name(v['mur'])}" if v["mur"] else ""), 12, "r", INK)

    _ex = sorted([e for e in load("exams") if e["sid"] == stu["id"] and e["date"][:7] == month], key=lambda e: e["date"])
    if _ex:
        title("الاختبارات")
        table([("التاريخ", 78), ("الاختبار", None), ("العلامة", 80)],
              [(e["date"], e["kind"] + (f" — الحزب {e['part']}" if e["kind"] == "اختبار حزب" and e["part"] else "") + (f"  ({e['note']})" if e["note"] else ""), f"{num(e['score']):g} / 20") for e in _ex], "")
    need(120)
    st_["y"] -= 34
    c.setFillColor(HexColor("#fbf6e6"))
    c.setStrokeColor(HexColor("#e6d9a8"))
    c.roundRect(L, st_["y"] - 56, R - L, 62, 8, stroke=1, fill=1)
    yy = st_["y"] - 12
    for ln in wrap("ملاحظة لأولياء الأمور: نرجو متابعة ابنكم في المراجعة والورد اليومي والحفظ ليكون التحصيل جيدا بإذن الله، مع ضرورة عدم التغيب عن الحلقة القرآنية إلا بعذر.", 12, R - L - 24):
        put(R - 12, yy, ln, 12, "r", HexColor("#5a4710"))
        yy -= 17
    st_["y"] -= 80
    put(L + 160, st_["y"], f"إدارة {SEC}", 12, "c", MUT)
    put(L + 160, st_["y"] - 16, DIR_N, 12, "c", INK)
    footer()
    c.save()
    return buf.getvalue()


def wa_link(text):
    return "https://wa.me/?text=" + urllib.parse.quote(text)


def dept_stats(mo):
    students = load("students")
    S, rk, tot = month_bundle(mo)
    act = [x for x in students if x["id"] in rk]
    pc = [S[x["id"]]["pct"] for x in act if S[x["id"]]["pct"] is not None]
    dv = [S[x["id"]]["dis"] for x in act if S[x["id"]]["dis"] is not None]
    due = [x for x in students if x.get("exempt") != "1"]
    paid_ids = {p_["sid"] for p_ in load("pay") if p_["month"] == mo}
    paid = [x for x in due if x["id"] in paid_ids]
    top = sorted(act, key=lambda x: (rk[x["id"]], x["name"]))[:10]
    rep = sorted([x for x in students if S[x["id"]]["absent"] >= ALERT_ABS], key=lambda x: -S[x["id"]]["absent"])
    return {"S": S, "rk": rk, "n": len(students), "act": len(act), "pct": round(sum(pc) / len(pc), 1) if pc else None,
            "dis": round(sum(dv) / len(dv), 2) if dv else None, "due": len(due), "paid": len(paid),
            "rate": round(100 * len(paid) / len(due)) if due else None, "top": top, "rep": rep,
            "aya": sum(S[x["id"]]["aya"] for x in students), "sessions": sum(len(S[x["id"]]["hl"]) + len(S[x["id"]]["ml"]) for x in students)}


def dept_pdf(mo):
    """تقرير شهري من صفحة واحدة للقسم كله (من أول الشهر إلى آخره)."""
    from reportlab.lib.colors import HexColor, white
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfgen import canvas

    if not os.path.exists(FONT):
        raise RuntimeError("ملف الخط Amiri-Regular.ttf غير موجود في GitHub بجانب app.py")
    if "Amiri" not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont("Amiri", FONT))
    D = dept_stats(mo)
    S = D["S"]
    INK, GOLD, PAPER, LINE, MUT = HexColor("#0a4a3e"), HexColor("#a9822a"), HexColor("#f3f5ee"), HexColor("#d6ddcb"), HexColor("#5f6f67")
    W, H = A4
    L, R = 36, W - 36
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    c.setTitle(f"تقرير القسم - {month_label(mo)}")

    def put(x, y, t, size=12, align="r", color=INK):
        c.setFont("Amiri", size)
        c.setFillColor(color)
        {"r": c.drawRightString, "l": c.drawString, "c": c.drawCentredString}[align](x, y, _shape(str(t)))

    c.setFillColor(INK)
    c.rect(0, H - 100, W, 100, stroke=0, fill=1)
    c.setFillColor(GOLD)
    c.rect(0, H - 104, W, 4, stroke=0, fill=1)
    lp = os.path.join(HERE, "logo.jpg")
    if os.path.exists(lp):
        c.setFillColor(white)
        c.roundRect(L, H - 90, 74, 74, 10, stroke=0, fill=1)
        c.drawImage(lp, L + 4, H - 86, 66, 66, preserveAspectRatio=True, mask="auto")
    put(R, H - 48, ASSOC, 24, "r", white)
    put(R, H - 74, f"{SEC}  ·  التقرير الشهري للقسم", 14, "r", HexColor("#e8d9a0"))
    y = H - 104 - 38
    put(W / 2, y, f"شهر {month_label(mo)}", 22, "c", INK)
    y -= 18
    put(W / 2, y, month_range_label(mo), 11, "c", MUT)
    y -= 16
    bw, gap, bh = (R - L - 30) / 4, 10, 66
    cards = [
        ("متوسط الحضور", f"{D['pct']:g}%" if D["pct"] is not None else "—", f"{D['act']} طالبا لهم تسجيل"),
        ("متوسط الانضباط", f"{D['dis']:.2f} / 3" if D["dis"] is not None else "—", disc_label(D["dis"])),
        ("نسبة الاشتراك", f"{D['rate']}%" if D["rate"] is not None else "—", f"سدّد {D['paid']} من {D['due']}"),
        ("آيات الحفظ", str(D["aya"]), f"{D['sessions']} حصة حفظ ومراجعة"),
    ]
    y0 = y - bh
    for k, (lab, val, sub) in enumerate(cards):
        x1 = R - k * (bw + gap)
        c.setFillColor(PAPER)
        c.setStrokeColor(LINE)
        c.roundRect(x1 - bw, y0, bw, bh, 8, stroke=1, fill=1)
        put(x1 - bw / 2, y0 + bh - 18, lab, 11, "c", MUT)
        put(x1 - bw / 2, y0 + bh - 42, val, 19, "c", INK)
        put(x1 - bw / 2, y0 + 8, sub, 9, "c", GOLD)
    y = y0 - 8

    def title(t):
        nonlocal y
        y -= 24
        put(R, y, t, 15, "r", INK)
        c.setStrokeColor(GOLD)
        c.setLineWidth(1.2)
        c.line(L, y - 6, R, y - 6)
        c.setLineWidth(1)
        y -= 10

    def table(cols, rows, empty):
        nonlocal y
        widths = [w or (R - L - sum(w2 for _, w2 in cols if w2)) for _, w in cols]
        y -= 19
        c.setFillColor(INK)
        c.rect(L, y, R - L, 19, stroke=0, fill=1)
        x = R
        for (h_, _), w in zip(cols, widths):
            put(x - 6, y + 5, h_, 10.5, "r", white)
            x -= w
        if not rows:
            y -= 22
            put(R - 6, y + 6, empty, 11, "r", MUT)
            return
        for k, row in enumerate(rows):
            y -= 19
            if k % 2 == 0:
                c.setFillColor(PAPER)
                c.rect(L, y, R - L, 19, stroke=0, fill=1)
            x = R
            for t, w in zip(row, widths):
                put(x - 6, y + 5, t, 11.5, "r", INK)
                x -= w

    title("أوائل الطلبة (العشرة الأوائل)")
    table([("الترتيب", 50), ("الطالب", 0), ("النقاط", 58), ("الانضباط", 64), ("الحضور", 56), ("المراجعة", 68), ("آيات الشهر", 66)],
          [(str(D["rk"][x["id"]]), x["name"], f"{S[x['id']]['score']:g}", f"{S[x['id']]['dis']:.2f}" if S[x["id"]]["dis"] is not None else "—",
            f"{S[x['id']]['pct']:g}%" if S[x["id"]]["pct"] is not None else "—", grade_name(S[x["id"]]["mur"]), str(S[x["id"]]["aya"])) for x in D["top"]],
          "لا توجد بيانات في هذا الشهر")
    title(f"الغيابات المتكررة ({ALERT_ABS} فأكثر دون عذر)")
    rep = D["rep"][:8]
    table([("الطالب", 0), ("غياب بلا عذر", 90), ("غياب بعذر", 80), ("الحضور", 62)],
          [(x["name"], str(S[x["id"]]["absent"]), str(S[x["id"]]["excused"]), f"{S[x['id']]['pct']:g}%" if S[x["id"]]["pct"] is not None else "—") for x in rep],
          "لا يوجد طالب بغياب متكرر هذا الشهر، والحمد لله")
    if len(D["rep"]) > 8:
        y -= 16
        put(R - 6, y, f"… و{len(D['rep']) - 8} طلبة آخرون", 10, "r", MUT)
    y -= 18
    put(R, y, "الترتيب بمجموع النقاط من 100: انضباط 25 + حضور 25 + مراجعة 20 + تقدم الحفظ 15 + تقدير الحفظ 15. الاشتراك لا يشمل المعفيين.", 9.5, "r", MUT)
    c.setStrokeColor(LINE)
    c.line(L, 44, R, 44)
    put(W / 2, 28, f"{ASSOC} – {SEC}", 10, "c", MUT)
    c.showPage()
    c.save()
    return buf.getvalue()


def month_summary(stu, mo, bundle, with_pin=True):
    S, rank, total = bundle
    v = S[stu["id"]]
    app = secret("app_url", "").rstrip("/")
    parts = [
        f"السلام عليكم ورحمة الله،\nتقرير ابنكم {stu['name']} لشهر {month_label(mo)} ({month_range_label(mo)}):",
        f"- الانضباط: {v['dis']:.2f} من 3 ({disc_label(v['dis'])})" if v["dis"] is not None else "- الانضباط: لم يُقيَّم بعد",
        f"- الحضور: {v['pct']:g}% (غياب {v['absent']}، غياب بعذر {v['excused']})" if v["pct"] is not None else "- الحضور: لا يوجد تسجيل",
        f"- الحفظ: {v['aya']} آية هذا الشهر · الإجمالي {v['tot_aya']} آية" if v["aya"] or v["tot_aya"] else "- الحفظ: لا يوجد تسجيل",
        f"- المراجعة: {grade_name(v['mur'])}",
        f"- الترتيب في الحلقة: {rank[stu['id']]} من {total} ({v['score']:g} نقطة من 100)" if stu["id"] in rank else "",
        "نرجو متابعته في المراجعة والورد اليومي والحفظ، وعدم التغيب عن الحلقة إلا بعذر.",
    ]
    if app:
        parts.append(f"للتفاصيل وتحميل التقرير (PDF): {app_link()}" + (f"&k={stu['pin']}" if with_pin and stu.get("pin") else "") + (f"\nالرمز السري: {stu['pin']}" if with_pin and stu.get("pin") else ""))
    return "\n".join(p for p in parts if p)


def monthly_ui(stu, key, staff=False):
    """اختيار الشهر ثم تجهيز التقرير وتنزيله (للمشايخ وللأولياء)."""
    mo = st.selectbox("الشهر", recent_months(), format_func=month_label, key=f"rm_{key}")
    if st.button("تجهيز التقرير الشهري", key=f"rb_{key}"):
        try:
            with st.spinner("جارٍ إعداد التقرير…"):
                bun = month_bundle(mo)
                st.session_state[f"rp_{key}"] = (mo, student_pdf(stu, mo, bun), month_summary(stu, mo, bun))
        except Exception as e:
            st.error(f"تعذّر إعداد التقرير: {e}")
    got = st.session_state.get(f"rp_{key}")
    if got and got[0] == mo:
        st.download_button("تحميل التقرير (PDF)", got[1], file_name=f"تقرير-{stu['name']}-{mo}.pdf", mime="application/pdf", key=f"rd_{key}", type="primary")
        if staff:
            st.link_button("إرسال ملخص الشهر للولي عبر واتساب", wa_link(got[2]))
            st.caption("واتساب لا يُرفق الملفات من الرابط: أرسل الملخص، ثم أرفق ملف PDF المحمَّل بنفسك إن أردت.")


def class_warn(day):
    if class_day(day):
        return
    hol = day in holidays()
    st.warning("هذا اليوم مسجَّل عطلة" if hol else "اليوم ليس يوم دراسة (لا دراسة الاثنين والخميس والجمعة)")
    st.caption("لن يُحتسب هذا اليوم ضمن «حصص الشهر» ولا في نسبة الحضور.")


def buddy_pairs(students):
    """يقترح ثنائيات من متقاربي الحفظ: الترتيب بعدد الآيات المحفوظة ثم الجمع بين كل متجاورين."""
    logs = [l for l in load("logs") if l["type"] == "hifz"]
    by = {}
    for l in logs:
        by.setdefault(l["sid"], []).append(l)
    info = []
    for x in students:
        m = memo_full(by.get(x["id"], []))
        rest = [k for k in m if k != 1]
        info.append({"x": x, "n": sum(len(v) for v in m.values()), "at": SURAHS[min(rest) - 1][0] if rest else "—"})
    info.sort(key=lambda r: (-r["n"], r["x"]["name"]))
    groups = [info[k:k + 2] for k in range(0, len(info), 2)]
    if len(groups) > 1 and len(groups[-1]) == 1:
        extra = groups.pop()
        groups[-1] += extra
    return groups


def buddy_ui(students):
    if len(students) < 2:
        return
    groups = buddy_pairs(students)
    with st.expander(f"رفيق الحفظ ({len(groups)})"):
        st.caption("طلبة متقاربو الحفظ في الحلقة كلها، يراجعون معا قبل التسميع. الاقتراح يتجدد تلقائيا كلما تقدّم الحفظ.")
        for g in groups:
            st.markdown(" ⇄ ".join(f"**{esc(r['x']['name'])}** ({r['n']} آية، عند {esc(r['at'])})" for r in g))


def auto_filled(hifz_logs):
    """السور التي عُدّت محفوظة تلقائيا دون أي تسجيل، وأدنى تسجيل حفظ جديد (غير الفاتحة) هو سببها."""
    low, cause = 115, None
    logged = set()
    for l in hifz_logs:
        if not is_new(l):
            continue
        a = aya_set(l)
        logged |= {sn for sn, _ in a}
        ks = [sn for sn, _ in a if sn != 1]
        if ks and min(ks) < low:
            low, cause = min(ks), l
    if not cause:
        return [], None
    return [sn for sn in range(low + 1, 115) if sn not in logged], cause


def autofill_check_ui(students):
    by = {}
    for l in load("logs"):
        if l["type"] == "hifz":
            by.setdefault(l["sid"], []).append(l)
    bad = []
    for x in students:
        miss, cause = auto_filled(by.get(x["id"], []))
        if miss:
            bad.append((len(miss), x, cause))
    with st.expander(f"فحص المحفوظ المحتسب تلقائيا ({len(bad)})"):
        st.caption("يُعدّ محفوظا كل ما بين سورة الناس وأدنى سورة سُجّلت للطالب. هؤلاء الطلبة عُدّت لهم سور دون تسجيل، فإن كان سبب ذلك تسجيلا خاطئا (سورة غير صحيحة مثلا) فعدّلوه أو احذفوه من تبويب «التقرير»، وسيُصحَّح الحساب فورا.")
        if not bad:
            st.success("لا طالب عُدّت له سور دون تسجيل.")
        for n, x, c in sorted(bad, key=lambda r: -r[0]):
            st.markdown(
                f"⚠️ **{esc(x['name'])}**: عُدّت {n} سورة محفوظة دون تسجيل — بسبب تسجيل "
                f"«{esc(c.get('detail', ''))}» بتاريخ {esc(c['date'])} (الشيخ {esc(c.get('teacher', ''))}، {esc(c.get('kind') or 'جديد')})"
            )


def first_name(full):
    """الاسم الشخصي: آخر كلمة في الاسم (اللقب أولا)، مع «محمد/عبد/أبو» إن سبقتها وكان الاسم من 3 كلمات فأكثر."""
    t = (full or "").split()
    if not t:
        return ""
    if len(t) >= 3 and t[-2] in ("محمد", "عبد", "أبو", "أبي"):
        return " ".join(t[-2:])
    return t[-1]


def surah_completions(hl):
    """[(تاريخ، سورة)] لكل سورة اكتمل حفظها (المقاطع الجديدة فقط) بترتيب الزمن."""
    cur, done, out = {}, set(), []
    for l in sorted([x for x in hl if is_new(x)], key=lambda x: (x["date"], x.get("ts") or "")):
        for sn, k in aya_set(l):
            cur.setdefault(sn, set()).add(k)
        for sn, v in cur.items():
            if sn not in done and len(v) == SURAHS[sn - 1][1]:
                done.add(sn)
                out.append((l["date"], sn))
    return out


def joy_events(logs_all, days=60, day=None):
    """أحداث تستحق بطاقة فرحة: سور أُتمّ حفظها حديثا. [{date, line1}] من الأحدث."""
    day = day or today()
    cut = _ago(day, days)
    ev = [{"date": d_, "line1": f"أتمّ حفظ سورة {SURAHS[sn - 1][0]}"} for d_, sn in surah_completions([l for l in logs_all if l["type"] == "hifz"]) if d_ >= cut]
    return sorted(ev, key=lambda e: e["date"], reverse=True)


def badge_line(tx):
    """نص الوسام كما يظهر على البطاقة."""
    return tx if tx.startswith("أتمّ") else f"نال وسام «{tx}»"


def _fit_font(draw, text, path, size, maxw, minsize=34):
    from PIL import ImageFont

    while True:
        f = ImageFont.truetype(path, size, layout_engine=ImageFont.Layout.BASIC)
        if draw.textlength(_shape(text), font=f) <= maxw or size <= minsize:
            return f
        size -= 2


def _wrap(draw, text, font, maxw):
    lines, cur = [], ""
    for w_ in text.split():
        t = (cur + " " + w_).strip()
        if cur and draw.textlength(_shape(t), font=font) > maxw:
            lines.append(cur)
            cur = w_
        else:
            cur = t
    if cur:
        lines.append(cur)
    return lines


@st.cache_data(show_spinner=False, max_entries=80)
def joy_png(name, line1, dua="بارك الله فيه وزاده حرصا وتوفيقا", sk=""):
    """بطاقة فرحة للمشاركة (صورة PNG 1080×1350) بشعار الجمعية."""
    import math
    from PIL import Image, ImageDraw, ImageFont

    if not os.path.exists(FONT):
        raise RuntimeError("ملف الخط Amiri-Regular.ttf غير موجود في GitHub بجانب app.py")
    W, H = 1080, 1350
    top, bot = (6, 53, 44), (10, 74, 62)
    img = Image.new("RGB", (W, H))
    px = ImageDraw.Draw(img)
    for y in range(H):
        t = y / H
        px.line([(0, y), (W, y)], fill=tuple(int(top[k] + (bot[k] - top[k]) * t) for k in range(3)))
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ld = ImageDraw.Draw(lay)
    step = 150
    for cx in range(0, W + step, step):  # شبكة نجوم ثمانية خفيفة
        for cy in range(0, H + step, step):
            r = 44
            for rot in (0, math.pi / 4):
                pts = [(cx + r * math.cos(rot + math.pi / 4 + k * math.pi / 2), cy + r * math.sin(rot + math.pi / 4 + k * math.pi / 2)) for k in range(4)]
                ld.polygon(pts, outline=(212, 175, 55, 34))
    img = Image.alpha_composite(img.convert("RGBA"), lay)
    d = ImageDraw.Draw(img)
    GOLD, GOLD2, WHITE = (212, 175, 55), (232, 207, 120), (250, 247, 235)
    d.rectangle([34, 34, W - 34, H - 34], outline=GOLD, width=5)
    d.rectangle([52, 52, W - 52, H - 52], outline=GOLD2, width=2)
    for x_, y_ in ((34, 34), (W - 34, 34), (34, H - 34), (W - 34, H - 34)):
        d.ellipse([x_ - 11, y_ - 11, x_ + 11, y_ + 11], fill=GOLD)

    def font(sz):
        return ImageFont.truetype(FONT, sz, layout_engine=ImageFont.Layout.BASIC)

    def center(y, text, f, fill):
        d.text((W / 2, y), _shape(text), font=f, fill=fill, anchor="mt")

    lp = os.path.join(HERE, "logo.jpg")
    if os.path.exists(lp):
        lg = Image.open(lp).convert("RGB")
        lg.thumbnail((190, 190))
        pw, ph = lg.size[0] + 24, lg.size[1] + 24
        x0, y0 = int(W / 2 - pw / 2), 80
        d.rounded_rectangle([x0 - 6, y0 - 6, x0 + pw + 6, y0 + ph + 6], radius=26, fill=GOLD)
        d.rounded_rectangle([x0, y0, x0 + pw, y0 + ph], radius=22, fill=(255, 255, 255))
        img.paste(lg, (x0 + 12, y0 + 12))
        d = ImageDraw.Draw(img)
    center(310, ASSOC, font(44), GOLD2)
    d.line([(W / 2 - 170, 380), (W / 2 + 170, 380)], fill=GOLD, width=2)
    center(410, "ما شاء الله", font(140), GOLD)
    nm_f = _fit_font(d, name, FONT, 112, W - 200)
    center(590, name, nm_f, WHITE)
    f2 = font(68)
    y = 800
    for ln in _wrap(d, line1, f2, W - 220)[:4]:
        center(y, ln, f2, WHITE)
        y += 104
    d.line([(W / 2 - 120, y + 20), (W / 2 + 120, y + 20)], fill=GOLD, width=2)
    fd = _fit_font(d, dua, FONT, 50, W - 200, 30)
    center(y + 60, dua, fd, GOLD2)
    center(H - 150, CITY, font(36), (170, 190, 180))
    buf = io.BytesIO()
    img.convert("RGB").save(buf, "PNG", optimize=True)
    return buf.getvalue()


def joy_card_ui(name, line1, key):
    """يعرض البطاقة مع زر التنزيل."""
    try:
        png = joy_png(name, line1, sk=SECKEY)
    except Exception as e:
        st.error(f"تعذّر إنشاء البطاقة: {e}")
        return
    st.image(png, width=320)
    st.download_button("تنزيل البطاقة للمشاركة", png, file_name=f"بطاقة-{name}.png", mime="image/png", key=f"jd_{key}")


def joy_staff_ui(students):
    """للشيوخ: بطاقات الفرحة. التفعيل بمفتاح حتى لا يثقل الحساب الحلقة."""
    with st.expander("بطاقات الفرحة للمشاركة"):
        on = st.toggle("إنشاء بطاقات الفرحة", key="joy_on")
        if not on:
            st.caption("بطاقة بصورة وشعار الجمعية عند إتمام سورة أو نيل وسام، تُرسل للولي للتشجيع.")
            return
        if not students:
            return
        stu = st.selectbox("الطالب", students, format_func=lambda x: x["name"], key="joy_s")
        L = [l for l in load("logs") if l["sid"] == stu["id"]]
        opts = [(e["line1"], f'{e["date"]} — {e["line1"]}') for e in joy_events(L)]
        if st.checkbox("تضمين أوسمة الشهر الماضي", key="joy_b"):
            pm = prev_month(today()[:7])
            v = month_bundle(pm)[0].get(stu["id"])
            opts += [(badge_line(tx), f"وسام {month_label(pm)} — {tx}") for _ic, tx in (v or {}).get("badges", [])]
        try:
            ww = week_winner(sk=SECKEY)
        except Exception:
            ww = None
        if ww and ww["sid"] == stu["id"]:
            opts.append(("طالب الأسبوع لتحسّنه الملحوظ", "طالب الأسبوع"))
        opts.append(("", "نص مخصص"))
        pick = st.selectbox("المناسبة", opts, format_func=lambda o: o[1], key="joy_p")
        txt = pick[0] if pick[0] else st.text_input("نص البطاقة", placeholder="مثال: أتمّ حفظ الجزء الثلاثين", key="joy_t")
        nm = st.text_input("الاسم على البطاقة", value=first_name(stu["name"]), key=f"joy_n{stu['id']}")
        if txt.strip() and nm.strip():
            joy_card_ui(nm.strip(), txt.strip(), "staff")
        else:
            st.caption("اكتب نص البطاقة والاسم.")


def last_week_range(day=None):
    """آخر أسبوع منتهٍ: من السبت إلى الجمعة (الجمعة يوم بلا حلقة، فالأسبوع يكتمل بها)."""
    d0 = dt.date.fromisoformat(day or today())
    end = d0 - dt.timedelta(days=(d0.weekday() - 4) % 7)
    return (end - dt.timedelta(days=6)).isoformat(), end.isoformat()


@st.cache_data(ttl=120, show_spinner=False)
def week_winner(day=None, sk=""):
    """طالب الأسبوع: الأكثر تحسنا عن معدّله هو (متوسط أسابيعه الثلاثة السابقة)، لا الأعلى نقاطا."""
    lo, hi = last_week_range(day)
    students, logs, att, disc, exams = (load(n) for n in ("students", "logs", "att", "disc", "exams"))
    W = month_stats((lo, hi), students, logs, att, disc, exams)
    d_lo, d_hi = dt.date.fromisoformat(lo), dt.date.fromisoformat(hi)
    PW = [month_stats(((d_lo - dt.timedelta(days=7 * k)).isoformat(), (d_hi - dt.timedelta(days=7 * k)).isoformat()), students, logs, att, disc, exams) for k in (1, 2, 3)]
    rows = []
    for x in students:
        v = W[x["id"]]
        if not v["has"] or v["present"] < 1:
            continue
        bs = [P[x["id"]]["score"] for P in PW if P[x["id"]]["has"] and P[x["id"]]["present"] >= 1]
        if not bs:
            continue
        base = sum(bs) / len(bs)
        rows.append({"sid": x["id"], "name": x["name"], "week": v["score"], "base": round(base, 1), "delta": round(v["score"] - base, 1)})
    rows.sort(key=lambda r: (r["delta"], r["week"]), reverse=True)
    return {"range": (lo, hi), "rows": rows[:5], "sid": rows[0]["sid"] if rows and rows[0]["delta"] >= WEEK_MIN_GAIN else None}


WEEK_MIN_GAIN = 3.0


def week_label(rng):
    a, b = rng
    return f"من {a[8:10]}/{a[5:7]} إلى {b[8:10]}/{b[5:7]}"


def week_ui():
    try:
        ww = week_winner(sk=SECKEY)
    except Exception as e:
        st.caption(f"تعذّر حساب طالب الأسبوع: {e}")
        return
    win = next((r for r in ww["rows"] if r["sid"] == ww["sid"]), None)
    with st.expander(f"طالب الأسبوع ({week_label(ww['range'])})" + (f" — {win['name']}" if win else "")):
        if not ww["rows"]:
            st.caption("لا بيانات كافية بعد: يلزم حضور الطالب في هذا الأسبوع وأسبوع سابق على الأقل.")
            return
        st.caption("يُختار الأكثر تحسنا عن معدّل أسابيعه الثلاثة السابقة (نقاط من 100)، لا الأعلى نقاطا. أقل تحسن مطلوب: " + f"{WEEK_MIN_GAIN:g} نقاط.")
        for r in ww["rows"]:
            mark = "🌟" if r["sid"] == ww["sid"] else ("▲" if r["delta"] > 0 else "▼" if r["delta"] < 0 else "=")
            st.markdown(f"{mark} **{esc(r['name'])}**: {r['base']:g} ← {r['week']:g} ({r['delta']:+g})")
        if not win:
            st.caption("لا أحد بلغ حدّ التحسن هذا الأسبوع.")


# ───────────── خلق قرآني لكل حلقة ─────────────
KHULUQ = [  # (الخلق، السورة، الآية، نص الآية، المعنى، التطبيق، سؤال للحلقة) — نص الآيات من مصحف المدينة (برواية حفص) كما في حزمة quran-json
    ('الصدق', 9, 119, 'يَـٰٓأَيُّهَا ٱلَّذِينَ ءَامَنُواْ ٱتَّقُواْ ٱللَّهَ وَكُونُواْ مَعَ ٱلصَّـٰدِقِينَ',
     'يأمرنا الله بتقواه وبمصاحبة الصادقين.',
     'قل الحقيقة ولو كانت صعبة، وإذا أخطأتَ فاعترف: أنا أخطأت.',
     'متى يصعب علينا قول الصدق؟ وماذا نفعل حينها؟'),
    ('الأمانة', 4, 58, 'إِنَّ ٱللَّهَ يَأۡمُرُكُمۡ أَن تُؤَدُّواْ ٱلۡأَمَٰنَٰتِ إِلَىٰٓ أَهۡلِهَا',
     'الأمانة أن نردّ كل حق إلى صاحبه.',
     'أعِد القلم أو الكتاب الذي استعرتَه، وحافظ على مصحف الحلقة وأدواتها.',
     'ما الأشياء التي أُؤتُمنتَ عليها اليوم؟'),
    ('بر الوالدين', 17, 23, 'وَقَضَىٰ رَبُّكَ أَلَّا تَعۡبُدُوٓاْ إِلَّآ إِيَّاهُ وَبِٱلۡوَٰلِدَيۡنِ إِحۡسَٰنًاۚ',
     'جعل الله الإحسان إلى الوالدين بعد عبادته مباشرة.',
     'قبّل يد والديك، وأجبهما فورا، وساعدهما في البيت قبل أن يطلبا.',
     'ما العمل الذي تفاجئ به والديك اليوم؟'),
    ('الصبر', 39, 10, 'إِنَّمَا يُوَفَّى ٱلصَّـٰبِرُونَ أَجۡرَهُم بِغَيۡرِ حِسَابٖ',
     'الصابرون لهم أجر عظيم لا يُحصى.',
     'عند التعب أو الغضب خذ نفسا عميقا وقل: أصبر لله، وانتظر دورك في التسميع بهدوء.',
     'متى نحتاج إلى الصبر في الحفظ؟'),
    ('الكلمة الطيبة', 2, 83, 'وَقُولُواْ لِلنَّاسِ حُسۡنٗا',
     'أمرنا الله أن نتكلم مع الناس بالحسنى.',
     'ابدأ كلامك بالسلام والابتسامة، وقل: شكرا، جزاك الله خيرا.',
     'ما أجمل كلمة سمعتها من زميل لك؟'),
    ('التواضع والحلم', 25, 63, 'وَعِبَادُ ٱلرَّحۡمَٰنِ ٱلَّذِينَ يَمۡشُونَ عَلَى ٱلۡأَرۡضِ هَوۡنٗا وَإِذَا خَاطَبَهُمُ ٱلۡجَٰهِلُونَ قَالُواْ سَلَٰمٗا',
     'عباد الرحمن يمشون بسكينة، وإذا خاطبهم الجاهلون ردّوا بالسلام.',
     'لا تتكبّر على أحد، وإذا أساء إليك زميل فقل: سلاما.',
     'كيف نردّ على من يغضبنا؟'),
    ('العفو والصفح', 24, 22, 'وَلۡيَعۡفُواْ وَلۡيَصۡفَحُوٓاْۗ أَلَا تُحِبُّونَ أَن يَغۡفِرَ ٱللَّهُ لَكُمۡۚ',
     'من أحبّ أن يغفر الله له فليعفُ عن الناس.',
     'سامح من أخطأ في حقك اليوم وقل له: عفوتُ عنك.',
     'من تريد أن تسامحه اليوم؟'),
    ('العدل والإحسان', 16, 90, 'إِنَّ ٱللَّهَ يَأۡمُرُ بِٱلۡعَدۡلِ وَٱلۡإِحۡسَٰنِ وَإِيتَآيِٕ ذِي ٱلۡقُرۡبَىٰ',
     'يأمرنا الله بإعطاء كل ذي حق حقه، وبالإحسان فوق ذلك.',
     'كن منصفا في اللعب والدور، وزِد على الواجب بمعروف صغير.',
     'ما الفرق بين العدل والإحسان؟'),
    ('التعاون', 5, 2, 'وَتَعَاوَنُواْ عَلَى ٱلۡبِرِّ وَٱلتَّقۡوَىٰۖ',
     'نتعاون على الخير ولا نتعاون على الظلم والعدوان.',
     'ساعد زميلك في المراجعة أو في ترتيب المكان، ولا تشاركه في خطأ.',
     'كيف نتعاون ونحن نراجع معا؟'),
    ('الأخوّة والإصلاح', 49, 10, 'إِنَّمَا ٱلۡمُؤۡمِنُونَ إِخۡوَةٞ فَأَصۡلِحُواْ بَيۡنَ أَخَوَيۡكُمۡۚ',
     'المؤمنون إخوة، فنسعى للصلح بينهم إذا اختلفوا.',
     'إذا تخاصم زميلان فاسعَ في الصلح بينهما بكلمة طيبة.',
     'ماذا تفعل إذا رأيت زميلين يتخاصمان؟'),
    ('ترك السخرية', 49, 11, 'يَـٰٓأَيُّهَا ٱلَّذِينَ ءَامَنُواْ لَا يَسۡخَرۡ قَوۡمٞ مِّن قَوۡمٍ عَسَىٰٓ أَن يَكُونُواْ خَيۡرٗا مِّنۡهُمۡ',
     'لا نسخر من أحد، فقد يكون خيرا منا.',
     'لا تضحك على خطأ زميلك في التلاوة، ولا تناده بلقب يكرهه.',
     'كيف نشعر إذا سخر منا أحد؟'),
    ('حفظ اللسان من الغيبة', 49, 12, 'وَلَا تَجَسَّسُواْ وَلَا يَغۡتَب بَّعۡضُكُم بَعۡضًاۚ أَيُحِبُّ أَحَدُكُمۡ أَن يَأۡكُلَ لَحۡمَ أَخِيهِ مَيۡتٗا فَكَرِهۡتُمُوهُۚ',
     'نهانا الله عن التجسس والغيبة، وشبّه الغيبة بأكل لحم الأخ.',
     'لا تذكر أحدا في غيابه بما يكره.',
     'ماذا نفعل إذا بدأ أحدهم بالغيبة؟'),
    ('الوفاء بالعهد', 17, 34, 'وَأَوۡفُواْ بِٱلۡعَهۡدِۖ إِنَّ ٱلۡعَهۡدَ كَانَ مَسۡـُٔولٗا',
     'العهد مسؤولية سنُسأل عنها.',
     'إذا وعدتَ بشيء فنفّذه: الحضور في الموعد، وحفظ ما اتفقنا عليه.',
     'ما وعدٌ قطعتَه وتريد الوفاء به؟'),
    ('الشكر', 14, 7, 'وَإِذۡ تَأَذَّنَ رَبُّكُمۡ لَئِن شَكَرۡتُمۡ لَأَزِيدَنَّكُمۡۖ',
     'من شكر الله زاده من فضله.',
     'قل: الحمد لله بعد كل نعمة، واشكر معلمك ووالديك.',
     'عدّد ثلاث نعم عندك.'),
    ('الاستئذان', 24, 27, 'يَـٰٓأَيُّهَا ٱلَّذِينَ ءَامَنُواْ لَا تَدۡخُلُواْ بُيُوتًا غَيۡرَ بُيُوتِكُمۡ حَتَّىٰ تَسۡتَأۡنِسُواْ وَتُسَلِّمُواْ عَلَىٰٓ أَهۡلِهَاۚ',
     'لا ندخل بيتا غير بيتنا حتى نستأذن ونسلّم على أهله.',
     'استأذن قبل الدخول إلى أي مكان، وسلّم عند دخولك الحلقة.',
     'كيف نستأذن بأدب؟'),
    ('رد السلام', 4, 86, 'وَإِذَا حُيِّيتُم بِتَحِيَّةٖ فَحَيُّواْ بِأَحۡسَنَ مِنۡهَآ أَوۡ رُدُّوهَآۗ',
     'إذا سلّم عليك أحد فرُدّ بأحسن منه أو بمثله.',
     'ابدأ بالسلام، وأجب بـ: وعليكم السلام ورحمة الله.',
     'كيف نردّ السلام بأحسن منه؟'),
    ('التثبّت من الأخبار', 49, 6, 'يَـٰٓأَيُّهَا ٱلَّذِينَ ءَامَنُوٓاْ إِن جَآءَكُمۡ فَاسِقُۢ بِنَبَإٖ فَتَبَيَّنُوٓاْ',
     'إذا جاءنا خبر من غير ثقة فلنتأكد قبل أن نصدّق أو ننقل.',
     'لا تنشر خبرا في الهاتف أو بين الزملاء حتى تتأكد منه.',
     'كيف نتأكد من صحة الخبر؟'),
    ('الأدب في المشي والصوت', 31, 19, 'وَٱقۡصِدۡ فِي مَشۡيِكَ وَٱغۡضُضۡ مِن صَوۡتِكَۚ',
     'نمشي باعتدال ونخفض أصواتنا.',
     'لا تصرخ في الحلقة ولا تجرِ في المسجد.',
     'لماذا نخفض أصواتنا في المسجد؟'),
    ('الإخلاص في العطاء', 76, 9, 'إِنَّمَا نُطۡعِمُكُمۡ لِوَجۡهِ ٱللَّهِ لَا نُرِيدُ مِنكُمۡ جَزَآءٗ وَلَا شُكُورًا',
     'نعطي لله، لا ننتظر من الناس جزاء ولا شكرا.',
     'افعل معروفا اليوم ولا تخبر به أحدا.',
     'ما معروف فعلته دون أن يعلم به أحد؟'),
    ('الإيثار', 59, 9, 'وَيُؤۡثِرُونَ عَلَىٰٓ أَنفُسِهِمۡ وَلَوۡ كَانَ بِهِمۡ خَصَاصَةٞۚ',
     'المؤمنون يقدّمون غيرهم على أنفسهم ولو كانوا محتاجين.',
     'قدّم زميلا في الدور، أو شاركه طعامك.',
     'ما شيء تحبه وتستطيع أن تُؤثر به غيرك؟'),
    ('العدل', 5, 8, 'ٱعۡدِلُواْ هُوَ أَقۡرَبُ لِلتَّقۡوَىٰۖ',
     'نعدل حتى مع من لا نحب، فالعدل أقرب للتقوى.',
     'لا تظلم أحدا ولو غضبتَ منه، وقل الحق ولو على نفسك.',
     'كيف نعدل بين زملائنا؟'),
    ('التوكل على الله', 65, 3, 'وَمَن يَتَوَكَّلۡ عَلَى ٱللَّهِ فَهُوَ حَسۡبُهُۥٓۚ',
     'من توكّل على الله كفاه.',
     'خذ بالأسباب: اجتهد في الحفظ والمراجعة، ثم توكّل على الله.',
     'ما الفرق بين التوكل والتواكل؟'),
    ('ذكر الله', 13, 28, 'أَلَا بِذِكۡرِ ٱللَّهِ تَطۡمَئِنُّ ٱلۡقُلُوبُ',
     'بذكر الله تطمئن القلوب.',
     'داوم على أذكار الصباح والمساء، وقل: سبحان الله كلما رأيت نعمة.',
     'ما الأذكار التي تحفظها؟'),
    ('الرفق واللين', 3, 159, 'فَبِمَا رَحۡمَةٖ مِّنَ ٱللَّهِ لِنتَ لَهُمۡۖ وَلَوۡ كُنتَ فَظًّا غَلِيظَ ٱلۡقَلۡبِ لَٱنفَضُّواْ مِنۡ حَوۡلِكَۖ',
     'لو كان النبي ﷺ فظّا غليظ القلب لانفضّ الناس من حوله، فاللين سبب المحبة.',
     'تكلّم بلين مع زملائك وإخوتك الصغار.',
     'كيف نعامل الصغار برفق؟'),
    ('كظم الغيظ', 3, 134, 'وَٱلۡكَٰظِمِينَ ٱلۡغَيۡظَ وَٱلۡعَافِينَ عَنِ ٱلنَّاسِۗ وَٱللَّهُ يُحِبُّ ٱلۡمُحۡسِنِينَ',
     'الله يحب الذين يكظمون غيظهم ويعفون عن الناس.',
     'إذا غضبتَ فاسكت واستعذ بالله، ثم تكلّم بهدوء.',
     'ماذا نفعل حين نغضب؟'),
    ('الإحسان إلى من أساء', 41, 34, 'وَلَا تَسۡتَوِي ٱلۡحَسَنَةُ وَلَا ٱلسَّيِّئَةُۚ ٱدۡفَعۡ بِٱلَّتِي هِيَ أَحۡسَنُ فَإِذَا ٱلَّذِي بَيۡنَكَ وَبَيۡنَهُۥ عَدَٰوَةٞ كَأَنَّهُۥ وَلِيٌّ حَمِيمٞ',
     'قابل الإساءة بالإحسان، فقد يتحول العدو إلى صديق.',
     'إذا أساء إليك أحد فابتسم وأحسن إليه.',
     'هل جرّبتَ أن تحسن إلى من أساء إليك؟'),
    ('طلب العلم', 20, 114, 'وَقُل رَّبِّ زِدۡنِي عِلۡمٗا',
     'نسأل الله أن يزيدنا علما.',
     'اسأل عما لا تفهمه، وقل قبل المراجعة: ربّ زدني علما.',
     'ما شيء تعلمته هذا الأسبوع؟'),
    ('حب القرآن', 54, 17, 'وَلَقَدۡ يَسَّرۡنَا ٱلۡقُرۡءَانَ لِلذِّكۡرِ فَهَلۡ مِن مُّدَّكِرٖ',
     'يسّر الله القرآن للحفظ والتذكّر.',
     'اقرأ وردك اليومي ولو صفحة واحدة، ولا تيأس من الحفظ.',
     'ما أحب سورة إليك ولماذا؟'),
    ('الدعاء', 40, 60, 'وَقَالَ رَبُّكُمُ ٱدۡعُونِيٓ أَسۡتَجِبۡ لَكُمۡۚ',
     'الله يعدنا بالاستجابة إذا دعوناه.',
     'ادعُ الله بالتوفيق قبل الحفظ وبعده.',
     'ما الدعاء الذي تدعو به كل يوم؟'),
    ('الدعاء للوالدين', 17, 24, 'وَقُل رَّبِّ ٱرۡحَمۡهُمَا كَمَا رَبَّيَانِي صَغِيرٗا',
     'علّمنا الله أن ندعو لوالدينا بالرحمة.',
     'ادعُ لوالديك بعد كل صلاة: ربّ ارحمهما كما ربياني صغيرا.',
     'كيف ربّاك والداك وأنت صغير؟'),
    ('مراقبة الله', 96, 14, 'أَلَمۡ يَعۡلَم بِأَنَّ ٱللَّهَ يَرَىٰ',
     'الله يرانا في كل وقت.',
     'افعل الصواب حتى لو لم يرك أحد، واستحضر أن الله يراك.',
     'كيف يساعدنا شعورنا بأن الله يرانا؟'),
    ('الاستقامة', 11, 112, 'فَٱسۡتَقِمۡ كَمَآ أُمِرۡتَ',
     'الاستقامة على الطاعة وعدم تجاوز الحد.',
     'حافظ على الحضور والورد كل يوم، فالقليل الدائم خير من الكثير المنقطع.',
     'ما العادة الحسنة التي تريد أن تدوم عليها؟'),
    ('المحافظة على الصلاة', 2, 238, 'حَٰفِظُواْ عَلَى ٱلصَّلَوَٰتِ وَٱلصَّلَوٰةِ ٱلۡوُسۡطَىٰ وَقُومُواْ لِلَّهِ قَٰنِتِينَ',
     'أمر الله بالمحافظة على الصلوات والقيام لله خاشعين.',
     'صلِّ في وقتك، وذكّر إخوتك بالصلاة بلطف.',
     'كيف نخشع في صلاتنا؟'),
    ('الإحسان في العمل', 2, 195, 'وَأَحۡسِنُوٓاْۚ إِنَّ ٱللَّهَ يُحِبُّ ٱلۡمُحۡسِنِينَ',
     'الله يحب المحسنين.',
     'أتقن ما تفعله: الحفظ والكتابة وترتيب الأغراض.',
     'ما العمل الذي يمكنك أن تتقنه أكثر؟'),
    ('الأحسن في القول', 17, 53, 'وَقُل لِّعِبَادِي يَقُولُواْ ٱلَّتِي هِيَ أَحۡسَنُۚ إِنَّ ٱلشَّيۡطَٰنَ يَنزَغُ بَيۡنَهُمۡۚ',
     'نقول الكلمة الأحسن لأن الشيطان يوقع الخلاف بين الناس.',
     'إذا كنت غاضبا فاختر الكلمة الأحسن أو اسكت.',
     'كيف نمنع الشيطان من الإفساد بيننا؟'),
    ('الطهارة والتوبة', 2, 222, 'إِنَّ ٱللَّهَ يُحِبُّ ٱلتَّوَّـٰبِينَ وَيُحِبُّ ٱلۡمُتَطَهِّرِينَ',
     'الله يحب التوّابين ويحب المتطهّرين.',
     'حافظ على نظافة بدنك وثيابك ومكانك، وتب إذا أخطأت.',
     'كيف نتعاون على نظافة مكان الحلقة؟'),
    ('الاجتهاد والسعي', 53, 39, 'وَأَن لَّيۡسَ لِلۡإِنسَٰنِ إِلَّا مَا سَعَىٰ',
     'للإنسان ما سعى، فالنجاح بالعمل لا بالتمنّي.',
     'اجتهد في المراجعة ولا تؤجّلها.',
     'ماذا فعلتَ لتتقدم هذا الأسبوع؟'),
    ('حفظ اللسان', 50, 18, 'مَّا يَلۡفِظُ مِن قَوۡلٍ إِلَّا لَدَيۡهِ رَقِيبٌ عَتِيدٞ',
     'كل كلمة نقولها يُسجّلها ملَكان رقيب عتيد.',
     'فكّر قبل أن تتكلم: إما كلمة خير وإما الصمت.',
     'ما الكلمات التي نتجنبها؟'),
    ('الاستعانة بالصبر والصلاة', 2, 153, 'يَـٰٓأَيُّهَا ٱلَّذِينَ ءَامَنُواْ ٱسۡتَعِينُواْ بِٱلصَّبۡرِ وَٱلصَّلَوٰةِۚ إِنَّ ٱللَّهَ مَعَ ٱلصَّـٰبِرِينَ',
     'الله مع الصابرين، والصبر والصلاة خير معين.',
     'حين يصعب الحفظ اصبر وصلِّ وادعُ الله.',
     'كيف تعيننا الصلاة على الحفظ؟'),
    ('التواصي بالخير', 3, 104, 'وَلۡتَكُن مِّنكُمۡ أُمَّةٞ يَدۡعُونَ إِلَى ٱلۡخَيۡرِ وَيَأۡمُرُونَ بِٱلۡمَعۡرُوفِ وَيَنۡهَوۡنَ عَنِ ٱلۡمُنكَرِۚ',
     'أن نكون أمة تدعو إلى الخير وتأمر بالمعروف.',
     'انصح زميلك بلطف إذا رأيته يخطئ.',
     'كيف ننصح بلطف دون أن نجرح؟'),
]


KH_EPOCH = dt.date(2026, 9, 1)


def khuluq_index(day_iso):
    """رقم خلق الحلقة: يتبدل مع كل يوم دراسة بالتتابع، ويتفق عليه الشيوخ الثلاثة."""
    d1 = dt.date.fromisoformat(day_iso)
    n = sum(1 for k in range((d1 - KH_EPOCH).days + 1) if (KH_EPOCH + dt.timedelta(days=k)).weekday() in CLASS_WD)
    return max(n - 1, 0) % len(KHULUQ)


def khuluq_for(day_iso):
    ov = cfg_get(f"kh_{day_iso}", "")
    k = int(ov) if ov.isdigit() and int(ov) < len(KHULUQ) else khuluq_index(day_iso)
    return k, KHULUQ[k]


def khuluq_ui(day_iso, admin):
    k, (title, sn, a, txt, meaning, practice, ask) = khuluq_for(day_iso)
    with st.expander(f"🌿 خلق الحلقة: {title}", expanded=class_day(day_iso)):
        st.markdown(
            f'<div class="note" style="line-height:2"><div style="font-size:1.25rem;text-align:center">﴿ {esc(txt)} ﴾</div>'
            f'<div class="meta" style="text-align:center">سورة {esc(SURAHS[sn - 1][0])} · الآية {a}</div>'
            f'<div><b>المعنى:</b> {esc(meaning)}</div><div><b>كيف نطبّقه:</b> {esc(practice)}</div>'
            f'<div><b>سؤال للحلقة:</b> {esc(ask)}</div></div>', unsafe_allow_html=True)
        st.caption("خلق جديد مع كل يوم دراسة، ويظهر للشيوخ الثلاثة نفسه. خصّص دقيقتين لتذكير الطلبة به قبل الحفظ أو بعده.")
        if admin:
            c1, c2 = st.columns([3, 1])
            pick = c1.selectbox("تغيير خلق هذه الحلقة", list(range(len(KHULUQ))), index=k, format_func=lambda j: KHULUQ[j][0], key=f"khs_{day_iso}")
            c2.write("")
            if c2.button("اعتماد", key=f"khb_{day_iso}") and pick != k:
                cfg_set(f"kh_{day_iso}", str(pick))
                st.rerun()


# ───────────── الإبلاغ المسبق عن الغياب ─────────────
PRE_REASONS = ["مرض", "موعد طبي", "سفر", "ظرف عائلي طارئ", "امتحان أو دراسة", "أخرى"]


def pre_map(day_iso):
    """الإبلاغات المسبقة ليوم معيّن: {معرّف الطالب: إبلاغ}."""
    return {p["sid"]: p for p in load("pre") if p["date"] == day_iso}


def day_word(d_iso):
    t = now().date()
    d1 = dt.date.fromisoformat(d_iso)
    n = (d1 - t).days
    w = "اليوم" if n == 0 else "غدا" if n == 1 else "بعد غد" if n == 2 else ""
    return (w + " — " if w else "") + f"{WEEKDAYS_AR[d1.weekday()]} {d1.strftime('%d/%m')}"


def pre_ui(stu, att):
    """للولي: زر إبلاغ الشيخ مسبقا بغياب الابن لعذر طارئ."""
    sid = stu["id"]
    t0 = now().date()
    mine_ = sorted([p for p in load("pre") if p["sid"] == sid and p["date"] >= t0.isoformat()], key=lambda p: p["date"])
    wds = {DAYS[k][1] for k in days_of(stu)} | {MDAYS[k][1] for k in mdays_of(stu)} or set(CLASS_WD)
    taken = {a["date"] for a in att} | {p["date"] for p in mine_}
    hol = holidays()
    days = [(t0 + dt.timedelta(days=k)).isoformat() for k in range(0, 15)]
    days = [d_ for d_ in days if class_day(d_, hol) and dt.date.fromisoformat(d_).weekday() in wds and d_ not in taken]
    with st.expander("🔔 إبلاغ مسبق بغياب ابني لعذر طارئ" + (f" ({len(mine_)})" if mine_ else ""), expanded=bool(mine_)):
        st.caption("أبلغوا الشيخ قبل الحلقة ليرتّب وقته ولا ينتظر ابنكم عبثا. يُحتسب الإبلاغ ضمن حدّ التبريرات الشهري.")
        for p in mine_:
            c1, c2 = st.columns([4, 1])
            c1.markdown(f"✅ **{day_word(p['date'])}** — السبب: {esc(p['why'])}")
            if c2.button("إلغاء", key=f"pc_{p['id']}"):
                write(STORE.delete, "pre", p["id"])
                audit("إلغاء إبلاغ مسبق بغياب", f"{stu['name']} · {p['date']}", by="ولي الأمر")
                st.rerun()
        if not days:
            st.info("لا توجد حلقة قادمة (خلال أسبوعين) يمكن الإبلاغ عنها.")
            return
        with st.form(f"pref_{sid}"):
            d_ = st.selectbox("يوم الغياب", days, format_func=day_word)
            r_ = st.selectbox("السبب", PRE_REASONS)
            n_ = st.text_input("تفاصيل (اختياري، ويلزم عند اختيار «أخرى»)", max_chars=100)
            if st.form_submit_button("إبلاغ الشيخ", type="primary"):
                why = (r_ if r_ != "أخرى" else "") + (" — " if r_ != "أخرى" and n_.strip() else "") + n_.strip()
                if r_ == "أخرى" and not n_.strip():
                    st.error("اكتب السبب عند اختيار «أخرى»")
                else:
                    _load.clear()
                    fresh_att = [a for a in load("att") if a["sid"] == sid]
                    fresh_pre = [p for p in load("pre") if p["sid"] == sid]
                    m_ = d_[:7]
                    used = sum(1 for a in fresh_att if a.get("by") == "parent" and a["date"][:7] == m_)
                    used += sum(1 for p in fresh_pre if p["date"][:7] == m_ and not any(a["date"] == p["date"] for a in fresh_att))
                    if any(p["date"] == d_ for p in fresh_pre):
                        st.error("سبق الإبلاغ عن هذا اليوم.")
                    elif used >= MAX_JUST:
                        st.error(f"استُنفد حدّ التبريرات لشهر {m_} ({MAX_JUST}). يرجى التقرب من المدرسة.")
                    else:
                        write(STORE.add, "pre", {"sid": sid, "date": d_, "why": why, "ts": now().strftime("%Y-%m-%d %H:%M")})
                        audit("إبلاغ مسبق بغياب", f"{stu['name']} · {d_} · {why}", by="ولي الأمر")
                        st.success("تم إبلاغ الشيخ. بارك الله فيكم.")
                        st.rerun()


def pre_banner(me, i):
    """للشيوخ: لافتة بأبناء أبلغ أولياؤهم عن غيابهم اليوم وغدا."""
    t0 = now().date()
    ds = [(t0 + dt.timedelta(days=k)).isoformat() for k in (0, 1)]
    S = {x["id"]: x for x in load("students")}
    parts = []
    for d_ in ds:
        nm = sorted(S[p["sid"]]["name"] for p in load("pre") if p["date"] == d_ and p["sid"] in S)
        if nm:
            parts.append(f"{'اليوم' if d_ == ds[0] else 'غدا'}: " + "، ".join(esc(n) for n in nm))
    if parts:
        st.markdown('<div class="note">🟠 أولياء أبلغوا بغياب أبنائهم مسبقا — ' + " · ".join(parts) + ". لا تنتظروهم، وسيظهر غيابهم بعذر في الحضور.</div>", unsafe_allow_html=True)


CURVE_WEEKS = 8


@st.cache_data(ttl=120, show_spinner=False)
def weekly_curve(n=CURVE_WEEKS, day=None, sk=""):
    """نقاط كل طالب (من 100) في آخر n أسبوعا منتهيا (سبت–جمعة): {معرّف: [{lo, score|None}]}."""
    lo0, hi0 = last_week_range(day)
    students, logs, att, disc, exams = (load(k) for k in ("students", "logs", "att", "disc", "exams"))
    d_lo, d_hi = dt.date.fromisoformat(lo0), dt.date.fromisoformat(hi0)
    out = {x["id"]: [] for x in students}
    for k in range(n - 1, -1, -1):
        lo, hi = d_lo - dt.timedelta(days=7 * k), d_hi - dt.timedelta(days=7 * k)
        W = month_stats((lo.isoformat(), hi.isoformat()), students, logs, att, disc, exams)
        for x in students:
            v = W[x["id"]]
            out[x["id"]].append({"lo": lo.isoformat(), "score": v["score"] if v["has"] else None})
    return out


def curve_trend(pts):
    """(نص الاتجاه، نوعه) من آخر ما سُجّل: متوسط آخر 3 أسابيع مقابل ما قبلها."""
    vals = [p["score"] for p in pts if p["score"] is not None]
    if len(vals) < 3:
        return "لا بيانات كافية بعد لتحديد الاتجاه.", "n"
    rec, old = vals[-3:], vals[:-3] or vals[:1]
    d_ = sum(rec) / len(rec) - sum(old) / len(old)
    if d_ >= 3:
        return "ابنكم في صعود، بارك الله فيه.", "up"
    if d_ <= -3:
        return "نتائج ابنكم في هبوط، نرجو متابعته والتواصل مع الشيخ.", "down"
    return "نتائج ابنكم مستقرة.", "flat"


def curve_html(pts):
    W_, H_, L_, R_, T_, B_ = 320, 150, 30, 14, 18, 30
    n = len(pts)
    xs = [L_ + (W_ - L_ - R_) * (k / max(n - 1, 1)) for k in range(n)]
    y = lambda v: T_ + (H_ - T_ - B_) * (1 - v / 100)
    g = "".join(f'<line x1="{L_}" y1="{y(v):.1f}" x2="{W_ - R_}" y2="{y(v):.1f}" style="stroke:var(--line,#dfe5d8)" stroke-width="1"/>'
                f'<text x="{L_ - 5}" y="{y(v) + 3:.1f}" font-size="9" text-anchor="end" style="fill:var(--mut,#6b7a72)">{v}</text>' for v in (0, 50, 100))
    segs, cur = [], []
    for x_, p in zip(xs, pts):
        if p["score"] is None:
            if cur:
                segs.append(cur)
            cur = []
        else:
            cur.append((x_, y(p["score"])))
    if cur:
        segs.append(cur)
    lines = "".join(f'<polyline points="{" ".join(f"{a:.1f},{b:.1f}" for a, b in sg)}" fill="none" style="stroke:var(--ink,#0a4a3e)" stroke-width="2.5" stroke-linejoin="round"/>' for sg in segs if len(sg) > 1)
    last = max((k for k, p in enumerate(pts) if p["score"] is not None), default=-1)
    dots = "".join(
        f'<circle cx="{x_:.1f}" cy="{y(p["score"]):.1f}" r="{5 if k == last else 3.5}" style="fill:{"var(--gold2,#d4af37)" if k == last else "var(--ink,#0a4a3e)"}"/>'
        f'<text x="{x_:.1f}" y="{y(p["score"]) - 8:.1f}" font-size="9.5" text-anchor="middle" style="fill:var(--ink,#0a4a3e)">{p["score"]:.0f}</text>'
        for k, (x_, p) in enumerate(zip(xs, pts)) if p["score"] is not None)
    lab = "".join(f'<text x="{x_:.1f}" y="{H_ - 10}" font-size="9" text-anchor="middle" style="fill:var(--mut,#6b7a72)">{p["lo"][8:10]}/{p["lo"][5:7]}</text>' for x_, p in zip(xs, pts))
    return (f'<svg viewBox="0 0 {W_} {H_}" width="100%" role="img" aria-label="منحنى النقاط الأسبوعية من 100" style="direction:ltr;max-width:520px">{g}{lines}{dots}{lab}</svg>')


def curve_ui(sid):
    try:
        pts = weekly_curve(sk=SECKEY).get(sid, [])
    except Exception as e:
        st.caption(f"تعذّر رسم المنحنى: {e}")
        return
    sec("منحنى التقدم الأسبوعي")
    if not any(p["score"] is not None for p in pts):
        st.markdown('<div class="empty">يظهر المنحنى بعد اكتمال أسبوع من الحلقات.</div>', unsafe_allow_html=True)
        return
    txt, kind = curve_trend(pts)
    vals = [p["score"] for p in pts if p["score"] is not None]
    dl = f" ({vals[-1] - vals[-2]:+g} عن الأسبوع الذي قبله)" if len(vals) >= 2 else ""
    cls = {"up": "pay ok", "down": "pay no"}.get(kind, "note")
    st.markdown(curve_html(pts), unsafe_allow_html=True)
    st.markdown(f'<div class="{cls}">{"📈 " if kind == "up" else "📉 " if kind == "down" else ""}{esc(txt)} نقاط آخر أسبوع: <b>{vals[-1]:g}</b> من 100{dl}.</div>', unsafe_allow_html=True)
    st.caption("النقاط من 100: الانضباط والحضور والمراجعة والحفظ. الأسابيع من الأقدم (يسارا) إلى الأحدث (يمينا)، ويُضاف الأسبوع بعد انتهائه يوم الجمعة. الأسبوع الخالي من الحلقات لا يظهر.")


def halaqa_tab(i):
    me = TEACHERS[i]
    is_h = me["t"] == "hifz"
    sec("حلقة اليوم")
    day = st.date_input("اليوم", value=now().date(), key=f"hd{i}").isoformat()
    class_warn(day)
    khuluq_ui(day, me.get("admin"))
    _pre = pre_map(day)
    if me.get("admin"):
        target_props_ui(load("students"))
        autofill_check_ui(sorted(load("students"), key=lambda x: x["name"]))
    _all = sorted([x for x in load("students") if me.get("admin") or mine(x, i)], key=lambda x: x["name"])
    _nf = need_follow(_all, day)
    with st.expander(f"يحتاجون متابعة ({len(_nf)})", expanded=bool(_nf)):
        if not _nf:
            st.caption("لا طالب يحتاج متابعة خاصة الآن، والحمد لله.")
        for x_, why_ in _nf:
            st.markdown(f"**{esc(x_['name'])}**: " + " · ".join(esc(w) for w in why_))
    buddy_ui(sorted(load("students"), key=lambda x: x["name"]))
    err_class_ui(load("students"), load("logs"))
    week_ui()
    joy_staff_ui(sorted(load("students"), key=lambda x: x["name"]))
    _exl = load("exams")
    _cand = [(x_, hizb_candidates(x_["id"], load("logs"), _exl)) for x_ in _all]
    _cand = [(x_, c_) for x_, c_ in _cand if c_]
    if _cand:
        with st.expander(f"مرشحون للاختبار ({len(_cand)})"):
            for x_, c_ in _cand:
                st.markdown(f"🎓 **{esc(x_['name'])}**: أتمّ " + "، ".join(f"الحزب {h}" for h in c_) + " — يُمتحن فيه من أوله إلى آخره.")
    vis = sorted([x for x in load("students") if me.get("admin") or mine(x, i)], key=lambda x: x["name"])
    if not vis:
        st.info("لا يوجد طلبة بعد.")
        return
    wd = dt.date.fromisoformat(day).weekday()
    code = next((k for k, (_, n) in MDAYS.items() if n == wd), None)
    sched = (lambda x: days_of(x)) if is_h else (lambda x: mdays_of(x))
    if code:
        due = [x for x in vis if not sched(x) or code in sched(x)]
        if len(due) < len(vis) and st.checkbox(f"عرض طلبة {MDAYS[code][0]} فقط حسب الجدول ({len(due)} من {len(vis)})", key=f"hdue{i}_{day}"):
            vis = due
    else:
        st.caption("هذا اليوم ليس من أيام الحلقة، وهذه كل الطلبة.")
    if not vis:
        st.info("لا طلبة في هذا اليوم.")
        return
    if me.get("admin") and day == now().date().isoformat():
        with st.expander("ضبط أوقات الصلاة لليوم (إن اختلفت عن التقويم)"):
            _mg, _is, _src = prayer_times(day)
            c1, c2 = st.columns(2)
            m1 = c1.text_input("المغرب (HH:MM)", value=_mg, key="ptm")
            m2 = c2.text_input("العشاء (HH:MM)", value=_is, key="pti")
            b1, b2 = st.columns(2)
            if b1.button("حفظ الأوقات", key="ptb"):
                if re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", m1.strip()) and re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", m2.strip()):
                    cfg_set(f"pt_{day}", f"{m1.strip()},{m2.strip()}")
                    audit("ضبط أوقات الحلقة", f"{day}: مغرب {m1.strip()} · عشاء {m2.strip()}")
                    st.rerun()
                else:
                    st.error("اكتب الوقت بصيغة 18:05 مثلا")
            if b2.button("إلغاء الضبط اليدوي", key="ptc"):
                cfg_set(f"pt_{day}", "")
                st.rerun()
    logs = load("logs")
    expl = {x["id"] for x in vis if code and code in sched(x)}
    vis = sorted(vis, key=lambda x: (x["id"] not in expl, x["name"]))
    st.caption("🟢 = مجدول لهذا اليوم، ويظهر أولا. يمكنك استدعاء أي طالب آخر للتسجيل عنده في أي وقت.")
    att = {a["sid"]: a for a in load("att") if a["date"] == day}
    dsc = {d["sid"]: d for d in load("disc") if d["date"] == day and d["teacher"] == me["n"]}
    keys = list(ATT)
    if day == now().date().isoformat():
        halaqa_left_note(sum(1 for x in vis if x["id"] not in att))
    st.caption(f"الحضور مسجَّل لـ {sum(1 for x in vis if x['id'] in att)} من {len(vis)} · الانضباط لـ {sum(1 for x in vis if x['id'] in dsc)}. اترك ما لا تريد تغييره دون اختيار.")
    with st.form(f"hf{i}_{day}"):
        pk = {}
        for x in vis:
            sid = x["id"]
            with st.container(border=True):
                st.markdown(("🟢 " if sid in expl else "") + f"**{esc(x['name'])}**" + (f" · م{esc(x['grp'])}" if x["grp"] else ""))
                if sid in _pre:
                    st.markdown(f'<div class="pay no">🟠 أبلغ وليّه مسبقا بغيابه: {esc(_pre[sid]["why"])}</div>', unsafe_allow_html=True)
                if not is_h:
                    _rec = recent_hifz(sid, logs, day)
                    if _rec:
                        st.caption("اقترح: " + " · ".join(range_label(r) for r in _rec[:2]))
                    _pk = review_pick([l for l in logs if l["sid"] == sid], day, 2)
                    if _pk:
                        st.caption("🔴 اسمع له اليوم: " + review_pick_text(_pk))
                    _st, _tot, _fr = stale_ranges(sid, logs, day)
                    if _st:
                        st.caption(f"⚠ لم يُراجَع منذ أسبوعين: {range_label(_st[0])}" + (f" (+{len(_st) - 1})" if len(_st) > 1 else ""))
                _et = err_top(logs, sid, 4)
                if _et:
                    st.caption("⚠ آيات سبق التعثّر فيها: " + err_top_text(_et))
                ca = st.radio("الحضور", keys, format_func=ATT.get, horizontal=True, key=f"ha_{i}_{day}_{sid}",
                              index=keys.index(att[sid]["status"]) if sid in att and att[sid]["status"] in keys else (keys.index("e") if sid in _pre else None))
                cd = st.radio("الانضباط", [3, 2, 1], format_func=DISC.get, horizontal=True, key=f"hdc_{i}_{day}_{sid}",
                              index=[3, 2, 1].index(int(dsc[sid]["score"])) if sid in dsc and dsc[sid]["score"] in ("1", "2", "3") else None)
                rec = st.checkbox("تسجيل حفظ" if is_h else "تسجيل مراجعة", key=f"hr_{i}_{day}_{sid}")
                last = next(iter(by_date([l for l in logs if l["sid"] == sid and l["type"] == "hifz" and aya_set(l)])), None)
                d_sur, d_a1 = 114, 1
                if is_h and last:
                    d_sur, d_a1 = int(last["sur"]), int(last["a2"]) + 1
                    if d_a1 > SURAHS[d_sur - 1][1]:
                        d_sur, d_a1 = max(d_sur - 1, 1), 1
                if not is_h:
                    _r = recent_hifz(sid, logs, day)
                    if _r:
                        d_sur, d_a1 = _r[0][0], _r[0][1]
                c1, c2, c3, c4 = st.columns([3, 1, 1, 2])
                sn = c1.selectbox("من سورة", list(range(1, 115)), index=d_sur - 1, format_func=lambda k: f"{k}. {SURAHS[k - 1][0]}", key=f"hs_{i}_{day}_{sid}")
                a1 = c2.number_input("من آية", min_value=1, max_value=286, value=d_a1, step=1, key=f"h1_{i}_{day}_{sid}")
                a2 = c3.number_input("إلى آية", min_value=1, max_value=286, value=max(d_a1, 1), step=1, key=f"h2_{i}_{day}_{sid}")
                gr = c4.selectbox("التقدير", GRADES_H if is_h else GRADES, key=f"hg_{i}_{day}_{sid}")
                en = st.selectbox("إلى سورة", [0] + list(range(1, 115)), format_func=lambda k: "نفس السورة" if k == 0 else f"{k}. {SURAHS[k - 1][0]}", key=f"he_{i}_{day}_{sid}")
                if is_h:
                    kd, nt = st.selectbox("نوع الحفظ", list(HK), format_func=HK.get, key=f"hk_{i}_{day}_{sid}"), ""
                else:
                    kd, nt = "", st.text_input("المطلوب إعادته / الأخطاء (أي سورة ليست جيدة يعيدها)", key=f"hn_{i}_{day}_{sid}")
                er = st.text_input("آيات التعثّر (اختياري: أرقام مفصولة بفاصلة، مثل 12، 14-16)", key=f"her_{i}_{day}_{sid}")
                pk[sid] = (x, ca, cd, rec, sn, int(a1), int(a2), gr, en, kd, nt, er)
        if st.form_submit_button("حفظ حلقة اليوم", type="primary"):
            errs, a_new, a_upd, d_new, d_upd, l_new = [], [], {}, [], {}, []
            for sid, (x, ca, cd, rec, sn, a1, a2, gr, en, kd, nt, er) in pk.items():
                if ca:
                    c = att.get(sid)
                    ex_ = {"why": _pre[sid]["why"], "by": "parent"} if sid in _pre and ca in ("a", "e") else {"why": "", "by": ""}
                    if ex_["by"]:
                        ca = "e"
                    if c:
                        if c["status"] != ca or (ex_["by"] and c.get("by") != "parent"):
                            a_upd[c["id"]] = {"status": ca, "teacher": me["n"], **ex_}
                    else:
                        a_new.append({"sid": sid, "date": day, "status": ca, "teacher": me["n"], **({"why": ex_["why"], "by": "parent"} if ex_["by"] else {})})
                if cd:
                    c = dsc.get(sid)
                    if c:
                        if str(cd) != c["score"]:
                            d_upd[c["id"]] = {"score": str(cd)}
                    else:
                        d_new.append({"sid": sid, "date": day, "teacher": me["n"], "score": str(cd)})
                if rec:
                    base = {"sid": sid, "date": day, "teacher": me["n"], "role": me["r"], "type": "hifz" if is_h else "mur", "grade": gr,
                            "note": nt.strip(), "kind": kd, "ts": str(int(time.time() * 1000))}
                    if is_h and gr == "لم يحفظ":
                        l_new.append({**base, "kind": "none", "detail": "لم يحفظ في هذه الحلقة"})
                        continue
                    en_ = en or sn
                    if not (1 <= a1 <= SURAHS[sn - 1][1]) or not (1 <= a2 <= SURAHS[en_ - 1][1]) or (en_ == sn and a1 > a2):
                        errs.append(f"{x['name']}: الآيات خارج السورة أو البداية بعد النهاية")
                        continue
                    err_s, err_m = parse_err(er, sn, a1, a2, en)
                    if err_m:
                        errs.append(f"{x['name']}: {err_m}")
                        continue
                    if not en or en == sn:
                        _hint = err_hint(logs, sid, {(sn, k_) for k_ in range(a1, a2 + 1)})
                        if _hint:
                            flash_add(f"تنبيه ({x['name']}): سبق أن تعثّر في هذا المقطع عند: {_hint}. راجع أخطاءه فيه.")
                    l_new.append({**base, "sur": str(sn), "a1": str(a1), "a2": str(a2), "sur2": str(en) if en and en != sn else "", "err": err_s,
                                  "detail": seg_text(segments(sn, a1, en_, a2), "" if is_h else "مراجعة ")})
            if errs:
                for e in errs:
                    st.error(e)
                st.stop()
            try:
                if a_new:
                    write(STORE.add_many, "att", a_new)
                if a_upd:
                    write(STORE.update_many, "att", a_upd)
                if d_new:
                    write(STORE.add_many, "disc", d_new)
                if d_upd:
                    write(STORE.update_many, "disc", d_upd)
                ids = write(STORE.add_many, "logs", l_new) if l_new else []
            except Exception as e:
                st.error(f"تعذّر الحفظ في الجدول: {explain(e)}")
                st.stop()
            have = {r["id"] for r in load("logs")}
            if ids and not all(k in have for k in ids):
                st.error("لم تُحفَظ بعض تسجيلات الحفظ/المراجعة في الجدول! أعد المحاولة، وإن تكرر فاضغط «فحص التخزين» في الإدارة.")
                st.stop()
            n = len(a_new) + len(a_upd) + len(d_new) + len(d_upd) + len(l_new)
            if n:
                audit("حلقة اليوم", f"{day}: حضور {len(a_new) + len(a_upd)}، انضباط {len(d_new) + len(d_upd)}، {'حفظ' if is_h else 'مراجعة'} {len(l_new)}")
            st.toast(f"✓ تم الحفظ ({n} تسجيلا)" if n else "لا تغييرات للحفظ")
            st.rerun()


def att_tab(i):
    me = TEACHERS[i]
    sec("تسجيل الحضور لكل الحلقة")
    day = st.date_input("اليوم", value=now().date(), key=f"bad{i}").isoformat()
    class_warn(day)
    st.caption("يسجّل كل شيخ حضور جميع الطلبة، لا طلبته وحدهم.")
    vis = sorted(load("students"), key=lambda s: s["name"])
    if not vis:
        st.info("لا يوجد طلبة بعد.")
        return
    wd = dt.date.fromisoformat(day).weekday()
    code = next((k for k, (_, n) in MDAYS.items() if n == wd), None)
    if code:
        sched = lambda x: days_of(x) + mdays_of(x)
        due = [x for x in vis if not sched(x) or code in sched(x)]
        if len(due) < len(vis) and st.checkbox(f"عرض طلبة هذا اليوم فقط ({MDAYS[code][0]}): {len(due)} من {len(vis)}", value=True, key=f"bdue{i}_{day}"):
            vis = due
    cur = {a["sid"]: a for a in load("att") if a["date"] == day}
    keys = list(ATT)
    _pre = pre_map(day)
    if any(s["id"] in _pre for s in vis):
        st.markdown('<div class="note">🟠 أبلغ أولياء هؤلاء بغيابهم مسبقا: ' + "، ".join(f"{esc(s['name'])} ({esc(_pre[s['id']]['why'])})" for s in vis if s["id"] in _pre) + "</div>", unsafe_allow_html=True)
    n_set = sum(1 for s in vis if s["id"] in cur)
    st.caption(f"سُجّل حضور {n_set} من {len(vis)} طالبا في هذا اليوم.")
    allp = st.checkbox("اعتبر الطلبة غير المحدَّدين حاضرين", key=f"bap{i}_{day}")
    with st.form(f"baf{i}_{day}"):
        picks = {}
        for s in vis:
            c = cur.get(s["id"])
            picks[s["id"]] = st.radio(
                s["name"], keys, format_func=ATT.get, horizontal=True,
                index=keys.index(c["status"]) if c and c["status"] in keys else (keys.index("e") if s["id"] in _pre else None),
                key=f"bar{i}_{day}_{s['id']}",
            )
        if st.form_submit_button("حفظ حضور الحلقة", type="primary"):
            add, upd = [], {}
            for sid, val in picks.items():
                val = val or ("p" if allp else None)
                if not val:
                    continue
                c = cur.get(sid)
                pe_ = {"why": _pre[sid]["why"], "by": "parent"} if sid in _pre and val in ("a", "e") else {"why": "", "by": ""}
                if pe_["by"]:
                    val = "e"
                if c:
                    if c["status"] != val or (pe_["by"] and c.get("by") != "parent"):
                        upd[c["id"]] = {"status": val, "teacher": me["n"], **pe_}
                else:
                    add.append({"sid": sid, "date": day, "status": val, "teacher": me["n"], **({"why": pe_["why"], "by": "parent"} if pe_["by"] else {})})
            if add:
                write(STORE.add_many, "att", add)
            if upd:
                write(STORE.update_many, "att", upd)
            if add or upd:
                audit("حضور جماعي", f"{day}: {len(add)} جديد، {len(upd)} معدَّل")
            st.toast(f"✓ تم الحفظ ({len(add)} جديد، {len(upd)} معدَّل)")
            st.rerun()


SUG_ST = {"": "جديد", "study": "قيد الدراسة", "done": "نُفّذ", "no": "غير مناسب"}


def sug_tab(i):
    me = TEACHERS[i]
    admin = me.get("admin")
    gen_u = str(secret("general_user", "osama" if SEEDED else "")).strip().lower()
    general = bool(gen_u) and me["u"] == gen_u  # المدير العام: يرى اقتراحات كل الأقسام
    cen = _central()
    store = cen if cen is not None else STORE

    def sug_write(fn, *a):
        r = getattr(store, fn)("sug", *a)
        _load.clear()
        _cload.clear()
        return r

    sec("اقتراحات لتحسين الموقع")
    if general:
        _cap = "هنا تصلك اقتراحات كل الأقسام ومديريها، ويمكنك إرسال اقتراحاتك أيضا."
    elif cen is not None:
        _cap = "اكتب أي فكرة تسهّل عملك في الحلقة أو تفيد الطلبة والأولياء، فتصل إلى مدير القسم والمدير العام."
    else:
        _cap = "اكتب أي فكرة تسهّل عملك في الحلقة أو تفيد الطلبة والأولياء، فتصل إلى مدير القسم."
    st.caption(_cap)
    if cen is None and st.session_state.get("_central_err"):
        st.warning("تعذّر الاتصال بجدول الاقتراحات المشترك، فتُحفظ اقتراحاتك مؤقتا في جدول قسمك فقط.")
    with st.form(f"sugf{i}", clear_on_submit=True):
        txt = st.text_area("اقتراحك", max_chars=600, height=110, placeholder="مثال: أريد أن يظهر لي كذا… أو أن يُضاف زر كذا…")
        ok = st.form_submit_button("إرسال الاقتراح", type="primary")
    if ok:
        if len(txt.strip()) < 5:
            st.warning("اكتب الاقتراح بوضوح (5 أحرف على الأقل).")
        else:
            sug_write("add", {"ts": stamp(), "sec": SEC, "who": me["n"], "text": txt.strip(), "status": "", "reply": ""})
            audit("اقتراح لتحسين الموقع", txt.strip()[:80])
            st.success("✓ وصل اقتراحك، جزاك الله خيرا.")
    allr = _cload(SECKEY) if cen is not None else load("sug")
    if general:
        rows = allr
    elif admin:
        rows = [r for r in allr if r.get("sec", "") == SEC]
    else:
        rows = [r for r in allr if r.get("sec", "") == SEC and r["who"] == me["n"]]
    rows = sorted(rows, key=lambda r: (r["ts"], r["id"]), reverse=True)
    if not rows:
        st.caption("لا اقتراحات بعد." if admin else "لم ترسل اقتراحات بعد.")
        return
    sec("كل الاقتراحات" if admin else "اقتراحاتي")
    for r in rows[:60]:
        stt = r.get("status", "") if r.get("status", "") in SUG_ST else ""
        head = f"{r['ts'][:16]} · {SUG_ST[stt]}"
        if admin:
            head = (f"{r.get('sec', '')} · " if general else "") + f"{r['who']} · " + head
        with st.expander(head):
            st.markdown(f'<div class="note">{esc(r["text"]).replace(chr(10), "<br>")}</div>', unsafe_allow_html=True)
            if r.get("reply"):
                st.markdown(f'<div class="pay ok">الرد: {esc(r["reply"])}</div>', unsafe_allow_html=True)
            own = r.get("sec", "") == SEC and r["who"] == me["n"]
            if own or admin:
                nt = st.text_area("نص الاقتراح (يمكنك تعديله)", value=r["text"], max_chars=600, height=90, key=f"sgt{r['id']}")
            if admin:
                c1, c2 = st.columns(2)
                ns = c1.selectbox("الحالة", list(SUG_ST), index=list(SUG_ST).index(stt), format_func=SUG_ST.get, key=f"sgs{r['id']}")
                nr = c2.text_input("رد قصير (اختياري)", value=r.get("reply", ""), key=f"sgr{r['id']}", max_chars=200)
            if own or admin:
                b1, b2 = st.columns(2)
                if b1.button("حفظ", key=f"sgk{r['id']}"):
                    if len(nt.strip()) < 5:
                        st.warning("اكتب الاقتراح بوضوح (5 أحرف على الأقل).")
                    else:
                        ch = {"text": nt.strip()}
                        if admin:
                            ch.update({"status": ns, "reply": nr.strip()})
                        sug_write("update", r["id"], ch)
                        audit("تعديل اقتراح", nt.strip()[:60])
                        st.rerun()
                if b2.button("حذف", key=f"sgd{r['id']}"):
                    sug_write("delete", r["id"])
                    audit("حذف اقتراح", r["text"][:60])
                    st.rerun()
    if admin:
        open_ = [r for r in rows if r.get("status", "") in ("", "study")]
        if open_:
            sec("نص الاقتراحات المفتوحة للنسخ")
            st.caption("انسخه وأرسله لمن يطوّر الموقع.")
            st.code("\n\n".join(f"- ({(r.get('sec', '') + ' · ') if general else ''}{r['who']}) {r['text']}" for r in open_), language=None)


ALERT_ABS = 3


def dup_ids(rows, keyf):
    seen, dups = set(), []
    for r in rows:
        k = keyf(r)
        if k in seen:
            dups.append(r["id"])
        else:
            seen.add(k)
    return dups


def admin_extras(students):
    app = secret("app_url", "").rstrip("/")
    mo = st.selectbox("شهر المتابعة", recent_months(), format_func=month_label, key="axmo")
    st.caption(f"الفترة: {month_range_label(mo)}")
    bun = month_bundle(mo)
    S, rk, tot = bun

    al = [(s, S[s["id"]]) for s in students if S[s["id"]]["absent"] >= ALERT_ABS]
    with st.expander(f"تنبيه الغياب المتكرر ({len(al)})", expanded=bool(al)):
        if not al:
            st.caption(f"لا يوجد طالب غاب {ALERT_ABS} مرات أو أكثر دون عذر في هذا الشهر.")
        for s, v in al:
            c1, c2 = st.columns([3, 2])
            c1.markdown(f"**{esc(s['name'])}**<br>غياب {v['absent']} · بعذر {v['excused']}", unsafe_allow_html=True)
            ds = "، ".join(d[8:10] + "/" + d[5:7] for d in v["abs_dates"])
            msg = (f"السلام عليكم ورحمة الله،\nنُعلمكم أن ابنكم {s['name']} تغيّب {v['absent']} مرات في شهر {month_label(mo)} ({ds}).\n"
                   f"نرجو التقرب من المدرسة لتبرير الغياب، وعدم التغيب عن الحلقة القرآنية إلا بعذر. جزاكم الله خيرا.")
            c2.link_button("مراسلة الولي", wa_link(msg))

    with st.expander("ملخص الشهر لأولياء الأمور (واتساب)"):
        st.caption("يُرسَل الملخص مع الرابط والرمز السري. أرفق ملف PDF يدويا إن أردت من بطاقة الطالب أو من ملف ZIP أسفل.")
        shown = False
        for s in students:
            if not S[s["id"]]["has"]:
                continue
            shown = True
            c1, c2 = st.columns([3, 2])
            c1.markdown(esc(s["name"]))
            c2.link_button("إرسال الملخص", wa_link(month_summary(s, mo, bun)))
        if not shown:
            st.caption("لا توجد بيانات في هذا الشهر.")

    with st.expander("زيارات الأولياء لصفحة أبنائهم"):
        V = load("visits")
        rows_ = []
        for s_ in students:
            last_, n_mo_, n_all_ = visit_info(s_["id"], V)
            rows_.append({"الطالب": s_["name"], "آخر زيارة": last_ or "لم يزر بعد", "زيارات هذا الشهر": n_mo_, "الإجمالي": n_all_})
        rows_.sort(key=lambda r: (r["آخر زيارة"] != "لم يزر بعد", r["آخر زيارة"]))
        st.caption("تُسجَّل الزيارة عند دخول الولي بالرمز أو بالرابط (مرة كل نصف ساعة على الأكثر). الذين لم يزوروا يظهرون أولا.")
        st.dataframe(rows_, width="stretch", hide_index=True)

    with st.expander("حذف السجلات المكررة"):
        L, A = load("logs"), load("att")
        dl = dup_ids(sorted(L, key=lambda x: x.get("ts", "")), lambda r: (r["sid"], r["date"], r["type"], r["detail"].strip(), r["grade"], r["note"].strip(), r["teacher"]))
        da = dup_ids(A, lambda r: (r["sid"], r["date"]))
        if not dl and not da:
            st.caption("لا توجد سجلات مكررة.")
        else:
            st.warning(f"عُثر على {len(dl)} تسجيل حفظ/مراجعة مكرر و{len(da)} تسجيل حضور مكرر. يُبقى الأقدم ويُحذف الباقي.")
            ok = st.checkbox("أؤكد حذف المكرر", key="dupok")
            if st.button("حذف المكرر", disabled=not ok, key="dupgo"):
                if dl:
                    write(STORE.delete_many, "logs", dl)
                if da:
                    write(STORE.delete_many, "att", da)
                audit("حذف المكرر", f"{len(dl)} تسجيل و{len(da)} حضور")
                st.toast("✓ تم حذف المكرر")
                st.rerun()

    with st.expander("إعلانات أولياء الأمور"):
        with st.form("annf", clear_on_submit=True):
            txt = st.text_area("نص الإعلان (يظهر في أعلى صفحة الأولياء)", height=80)
            use_u = st.checkbox("تحديد تاريخ انتهاء")
            until = st.date_input("يظهر حتى", value=now().date() + dt.timedelta(days=7))
            if st.form_submit_button("نشر الإعلان", type="primary"):
                if not txt.strip():
                    st.error("اكتب نص الإعلان")
                else:
                    write(STORE.add, "ann", {"date": today(), "text": txt.strip(), "until": until.isoformat() if use_u else "", "by": who()})
                    audit("نشر إعلان", txt.strip()[:80])
                    st.rerun()
        anns = sorted(load("ann"), key=lambda a: a["date"], reverse=True)
        for a in anns[:15]:
            c1, c2 = st.columns([4, 1])
            exp = a["until"] and a["until"] < today()
            c1.markdown(f"{esc(a['text'])}<br><small>{esc(a['date'])}" + (f" · حتى {esc(a['until'])}" if a["until"] else "") + (" · منتهٍ" if exp else "") + "</small>", unsafe_allow_html=True)
            if c2.button("حذف", key=f"anr{a['id']}"):
                write(STORE.delete, "ann", a["id"])
                audit("حذف إعلان", a["text"][:80])
                st.rerun()

    with st.expander("الأوائل في صفحة الأولياء"):
        on = cfg_get("honor") == "1"
        v = st.checkbox("أظهر «الأوائل في الشهر» (أول ثلاثة بالاسم) في تبويب التقرير لأولياء الأمور", value=on, key="honorcb")
        st.caption("لا تظهر أرقام ترتيب غير الثلاثة الأوائل. يمكنك إيقافه في أي وقت.")
        if v != on:
            cfg_set("honor", "1" if v else "0")
            audit("الأوائل", "تفعيل" if v else "إيقاف")
            st.rerun()

    with st.expander("فحص التخزين"):
        if not hasattr(STORE, "diagnose"):
            st.caption("وضع تجريبي: لا يوجد جدول Google متصل.")
        elif st.button("فحص الجدول واختبار الكتابة", key="diagbtn"):
            try:
                for ln in STORE.diagnose():
                    st.text(ln)
                tid = STORE.add("cfg", {"key": "_test", "val": "1"})
                _load.clear()
                ok = any(x["id"] == tid for x in load("cfg"))
                STORE.delete("cfg", tid)
                _load.clear()
                (st.success if ok else st.error)("اختبار الكتابة والقراءة: " + ("نجح ✓" if ok else "فشل ✗"))
            except Exception as e:
                st.error(f"فشل الفحص: {explain(e)}")

    with st.expander("سجل التعديلات"):
        rows = sorted(load("audit"), key=lambda r: r["ts"], reverse=True)[:150]
        if rows:
            st.dataframe([{"الوقت": r["ts"], "من": r["who"], "الإجراء": r["act"], "التفاصيل": r["detail"]} for r in rows], width="stretch", hide_index=True)
        else:
            st.caption("لا توجد تعديلات مسجَّلة بعد.")


def disc_tab(i):
    me = TEACHERS[i]
    sec("تقييم الانضباط اليومي")
    st.caption("قيّم انضباط كل الطلبة في الحلقة: 3 منضبط · 2 متوسط · 1 غير منضبط. يُحسب معدل الانضباط الشهري من جميع التقييمات.")
    day = st.date_input("اليوم", value=now().date(), key=f"dd{i}").isoformat()
    students = sorted(load("students"), key=lambda s: s["name"])
    if not students:
        st.info("لا يوجد طلبة بعد.")
        return
    mine_rows = {d["sid"]: d for d in load("disc") if d["date"] == day and d["teacher"] == me["n"]}
    st.caption(f"قيّمتَ {len(mine_rows)} من {len(students)} طالبا في هذا اليوم.")
    with st.form(f"df{i}_{day}"):
        picks = {}
        for s in students:
            cur = mine_rows.get(s["id"])
            picks[s["id"]] = st.radio(
                s["name"], [3, 2, 1], format_func=DISC.get, horizontal=True,
                index=[3, 2, 1].index(int(cur["score"])) if cur and cur["score"] in ("1", "2", "3") else None,
                key=f"dr{i}_{day}_{s['id']}",
            )
        if st.form_submit_button("حفظ التقييم", type="primary"):
            add, upd = [], {}
            for sid, val in picks.items():
                if val is None:
                    continue
                cur = mine_rows.get(sid)
                if cur:
                    if str(val) != cur["score"]:
                        upd[cur["id"]] = {"score": str(val)}
                else:
                    add.append({"sid": sid, "date": day, "teacher": me["n"], "score": str(val)})
            if add:
                write(STORE.add_many, "disc", add)
            if upd:
                write(STORE.update_many, "disc", upd)
            if add or upd:
                audit("تقييم الانضباط", f"{day}: {len(add)} جديد، {len(upd)} معدَّل")
            st.success(f"✓ تم الحفظ ({len(add)} جديد، {len(upd)} معدَّل)")
            st.rerun()


# ───────────────────────── المراسلة وزيارات الأولياء ─────────────────────────
TKEY = {t["u"]: t for t in TEACHERS}
MAX_MSG_DAY = 5


def stamp():
    return now().strftime("%Y-%m-%d %H:%M:%S")


def thread_to(m):
    """الشيخ الذي تخصّه المحادثة: المستلِم إن كانت من الولي، والمرسِل إن كانت رداً."""
    return m["to"] if m["who"] == "parent" else m["who"]


def unread_count(i):
    me = TEACHERS[i]
    return sum(1 for m in load("msg") if m["who"] == "parent" and m["read"] != "1" and (me.get("admin") or m["to"] == me["u"]))


def bubbles(msgs, me_is_parent):
    out = []
    for m in msgs:
        mine = (m["who"] == "parent") == me_is_parent
        who_ = "ولي الأمر" if m["who"] == "parent" else TKEY[m["who"]]["n"] if m["who"] in TKEY else m["who"]
        to_ = "" if m["who"] != "parent" else f" ← {TKEY[m['to']]['n']}" if m["to"] in TKEY else ""
        new = (m["who"] == "parent" and m["read"] != "1") if not me_is_parent else (m["who"] != "parent" and m["read"] != "1")
        out.append(f'<div class="bub{" me" if mine else ""}{" new" if new else ""}"><div class="mt">{esc(who_)}{esc(to_)} · {esc(m["ts"][:16])}{" · جديد" if new else ""}</div>{esc(m["text"]).replace(chr(10), "<br>")}</div>')
    return "".join(out)


def log_visit(sid):
    """يسجّل دخول الولي لصفحة ابنه مرة واحدة في الجلسة، وبفاصل نصف ساعة على الأقل."""
    if st.session_state.get("visit_sid") == sid:
        return
    st.session_state["visit_sid"] = sid
    try:
        mine_ = [v["ts"] for v in load("visits") if v["sid"] == sid]
        last = max(mine_) if mine_ else ""
        if last:
            if (now().replace(tzinfo=None) - dt.datetime.strptime(last[:16], "%Y-%m-%d %H:%M")).total_seconds() < 1800:
                return
        STORE.add("visits", {"sid": sid, "ts": now().strftime("%Y-%m-%d %H:%M")})
        _load.clear()
    except Exception:
        pass


def visit_info(sid, visits=None):
    v = sorted(x["ts"] for x in (visits if visits is not None else load("visits")) if x["sid"] == sid)
    mo = today()[:7]
    return (v[-1] if v else ""), sum(1 for t in v if t[:7] == mo), len(v)


def eff_target(s):
    return int(num(s.get("target"))) or hifz_target()


def ayat_to_reach(sn, memo):
    """عدد الآيات التي بقيت ليصل الطالب إلى سورة sn (من الناس صعودا) بحسب محفوظه في memo."""
    return sum(max(0, SURAHS[k - 1][1] - len(memo.get(k, ()))) for k in range(sn, 115))


def surah_reached(target, memo):
    """أبعد سورة يبلغها الطالب إن حفظ target آية جديدة من حيث وصل."""
    cum, last = 0, None
    for k in range(114, 1, -1):
        need = SURAHS[k - 1][1] - len(memo.get(k, ()))
        if need <= 0:
            continue
        cum += need
        last = k
        if cum >= target:
            return k
    return last


def parent_target_ui(stu):
    """اقتراح الولي لهدف الشهر بالسور (لا بعدد الآيات): يبقى اقتراحا، والقرار للشيخ."""
    sid = stu["id"]
    sec("هدف الحفظ الشهري")
    month = today()[:7]
    hl = [l for l in load("logs") if l["sid"] == sid and l["type"] == "hifz"]
    memo_now = memo_full(hl)
    memo_start = memo_full([l for l in hl if l["date"][:7] < month])
    cur = eff_target(stu)
    reach = surah_reached(cur, memo_start)
    stt, pv, ps = stu.get("pstatus", ""), stu.get("ptarget", ""), stu.get("psur", "")
    own = int(num(stu.get("target")))
    lab = lambda k: f"سورة {SURAHS[int(k) - 1][0]}" if str(k).isdigit() and 1 <= int(k) <= 114 else ""
    st.markdown(f'<div class="note">هدف ابنكم هذا الشهر: <b>الوصول إلى نحو {lab(reach) or "—"}</b> ({"حدّده الشيخ" if own else "الهدف العام"}). '
                f'يمكنكم اقتراح السورة التي تناسب قدرته، والقرار النهائي للشيخ.</div>', unsafe_allow_html=True)
    prop = f"الوصول إلى {lab(ps)}" if lab(ps) else f"{pv} آية"
    msg = {"pending": (f"اقتراحكم ({prop}) بانتظار قرار الشيخ.", "note"), "accepted": (f"✓ اعتمد الشيخ اقتراحكم: {prop}.", "pay ok"),
           "rejected": (f"لم يُعتمد اقتراحكم ({prop})، والهدف الحالي: الوصول إلى نحو {lab(reach)}.", "pay no"),
           "set": (f"حدّد الشيخ الهدف: الوصول إلى نحو {lab(reach)}.", "pay ok")}.get(stt)
    if msg:
        st.markdown(f'<div class="{msg[1]}">{msg[0]}</div>', unsafe_allow_html=True)
    rest = [sn for sn in memo_now if sn != 1]
    f0 = min(rest) if rest else 115
    opts = list(range(min(f0, 114), max(min(f0, 114) - 20, 1), -1))
    with st.form("ptg"):
        sn = st.selectbox("السورة التي تقترحون أن يصل إليها ابنكم آخر هذا الشهر", opts,
                          format_func=lambda k: f"{k}. {SURAHS[k - 1][0]}" + (" (سورته الحالية)" if k == f0 else ""))
        if st.form_submit_button("إرسال الاقتراح إلى الشيخ"):
            need = max(1, min(600, ayat_to_reach(int(sn), memo_start)))
            write(STORE.update, "students", sid, {"ptarget": str(need), "psur": str(int(sn)), "pstatus": "pending"})
            audit("اقتراح هدف حفظ", f"{stu['name']}: الوصول إلى سورة {SURAHS[int(sn) - 1][0]} (≈{need} آية)", by="ولي الأمر")
            st.toast("✓ وصل اقتراحكم إلى الشيخ")
            st.rerun()


def target_props_ui(students):
    """للمدير: قرارات اقتراحات الأولياء لأهداف الحفظ."""
    pend = [x for x in students if x.get("pstatus") == "pending"]
    with st.expander(f"اقتراحات أهداف الحفظ من الأولياء ({len(pend)})", expanded=bool(pend)):
        if not pend:
            st.caption("لا اقتراحات بانتظار قرارك.")
        for x in pend:
            _ps = x.get("psur", "")
            _sl = f"الوصول إلى سورة {SURAHS[int(_ps) - 1][0]} " if _ps.isdigit() and 1 <= int(_ps) <= 114 else ""
            st.markdown(f"**{esc(x['name'])}**: الهدف الحالي {eff_target(x)} آية · اقتراح الولي **{esc(_sl)}(≈ {esc(x.get('ptarget', ''))} آية)**")
            c1, c2, c3 = st.columns([2, 1, 1])
            nv = c1.number_input("الهدف الذي تعتمده", min_value=5, max_value=300, value=int(num(x.get("ptarget"))) or 30, step=5, key=f"tpv{x['id']}", label_visibility="collapsed")
            if c2.button("اعتماد", key=f"tpa{x['id']}", type="primary"):
                same = int(nv) == int(num(x.get("ptarget")))
                write(STORE.update, "students", x["id"], {"target": str(int(nv)), "pstatus": "accepted" if same else "set"})
                audit("هدف حفظ", f"{x['name']}: {int(nv)} آية ({'اقتراح الولي' if same else 'قيمة أخرى'})")
                st.rerun()
            if c3.button("رفض", key=f"tpr{x['id']}"):
                write(STORE.update, "students", x["id"], {"pstatus": "rejected"})
                audit("رفض اقتراح هدف", x["name"])
                st.rerun()


def parent_msgs_tab(stu):
    sid = stu["id"]
    opts = {U0: f"{DIR_N} (الحفظ والإدارة)"}
    rv = None if SOLO else {"1": U1, "2": U2}.get(stu["grp"])
    if rv:
        opts[rv] = f'{TKEY[rv]["n"]} (المراجعة)'
    sec("مراسلة الشيخ")
    with st.form("pmsg", clear_on_submit=True):
        to = st.radio("إلى", list(opts), format_func=opts.get, horizontal=True)
        txt = st.text_area("رسالتكم", max_chars=500, height=100, placeholder="اكتبوا رسالتكم هنا…")
        if st.form_submit_button("إرسال", type="primary"):
            n_today = sum(1 for m in load("msg") if m["sid"] == sid and m["who"] == "parent" and m["ts"][:10] == today())
            if not txt.strip():
                st.error("اكتبوا الرسالة أولا")
            elif n_today >= MAX_MSG_DAY:
                st.error(f"بلغتم الحد اليومي ({MAX_MSG_DAY} رسائل). يمكنكم المراسلة غدا.")
            else:
                try:
                    write(STORE.add, "msg", {"sid": sid, "who": "parent", "to": to, "ts": stamp(), "text": txt.strip(), "read": ""})
                    st.toast("✓ وصلت رسالتكم إلى الشيخ")
                    st.rerun()
                except Exception as e:
                    st.error(f"تعذّر الإرسال: {explain(e)}")
    M = sorted([m for m in load("msg") if m["sid"] == sid], key=lambda m: m["ts"])
    _unr = [m["id"] for m in M if m["who"] != "parent" and m["read"] != "1"]
    if M:
        sec("المحادثة")
        st.markdown(bubbles(M[-30:], True), unsafe_allow_html=True)
        if _unr and st.button("تم الاطلاع على الردود", key="pread", type="primary"):
            write(STORE.update_many, "msg", {x: {"read": "1"} for x in _unr})
            st.rerun()
    else:
        st.markdown('<div class="empty">لا توجد رسائل بعد. يردّ عليكم الشيخ هنا، فافتحوا هذه الصفحة لاحقا لقراءة الرد.</div>', unsafe_allow_html=True)


def msgs_tab(i):
    me = TEACHERS[i]
    students = {s["id"]: s for s in load("students")}
    allm = [m for m in load("msg") if m["sid"] in students]
    threads = {}
    for m in allm:
        t = thread_to(m)
        if me.get("admin") or t == me["u"]:
            threads.setdefault((m["sid"], t), []).append(m)
    sec("رسائل الأولياء")
    if not threads:
        st.markdown('<div class="empty">لا توجد رسائل من الأولياء بعد.</div>', unsafe_allow_html=True)
        return

    def info(k):
        ms = sorted(threads[k], key=lambda m: m["ts"])
        un = sum(1 for m in ms if m["who"] == "parent" and m["read"] != "1")
        return ms, un

    order = sorted(threads, key=lambda k: (-info(k)[1], [-ord(c) for c in info(k)[0][-1]["ts"]]))
    for k in order:
        ms, un = info(k)
        sid_, tk = k
        with st.expander(f"{students[sid_]['name']} — {TKEY[tk]['n'] if tk in TKEY else tk}" + (f"  ·  {un} جديدة" if un else ""), expanded=bool(un)):
            st.markdown(bubbles(ms[-30:], False), unsafe_allow_html=True)
            with st.form(f"rf{sid_}_{tk}", clear_on_submit=True):
                rt = st.text_area("ردّك", max_chars=500, height=90, key=f"rt{sid_}_{tk}")
                c1, c2 = st.columns(2)
                send = c1.form_submit_button("إرسال الرد", type="primary")
                mark = c2.form_submit_button("تحديد كمقروءة")
            ids = [m["id"] for m in ms if m["who"] == "parent" and m["read"] != "1"]
            if send:
                if not rt.strip():
                    st.error("اكتب الرد أولا")
                else:
                    write(STORE.add, "msg", {"sid": sid_, "who": me["u"], "to": "parent", "ts": stamp(), "text": rt.strip(), "read": ""})
                    if ids:
                        write(STORE.update_many, "msg", {x: {"read": "1"} for x in ids})
                    audit("ردّ على ولي", students[sid_]["name"])
                    st.rerun()
            elif mark and ids:
                write(STORE.update_many, "msg", {x: {"read": "1"} for x in ids})
                st.rerun()


# ───────────────────────── صفحة الأولياء ─────────────────────────
def find_pin(text, students):
    """يقبل الرمز ملصوقا بأي شكل: بأرقام عربية أو بمسافات أو داخل جملة كاملة، ويعيد الرمز الصحيح أو None."""
    t = str(text).translate(str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789"))
    pins = {x["pin"] for x in students if x["pin"]}
    for c in [t.strip(), "".join(ch for ch in t if ch.isdigit()), *re.findall(r"\d{6}", t)]:
        if c in pins:
            return c
    return None


def parent_view():
    header("متابعة الطالب", basmala=True)
    pin = st.session_state.get("ppin")
    k = st.query_params.get("k")
    if not pin and k:
        # الرابط الذي يحمل الرمز يفتح صفحة الابن مباشرة دون لصق
        try:
            del st.query_params["k"]
        except KeyError:
            pass
        if not blocked():
            fp = find_pin(k, load("students"))
            if fp:
                st.session_state.ppin = fp
                st.rerun()
            note_fail()
    if not pin:
        sec("دخول ولي الأمر")
        st.markdown('<div class="lead">أدخل الرمز السري الخاص بابنكم، وهو الرمز الذي أرسلته إليكم الإدارة.</div>', unsafe_allow_html=True)
        with st.form("pf"):
            p = st.text_input("الرمز السري", max_chars=300, placeholder="اكتب الرمز أو الصقه هنا")
            ok = st.form_submit_button("عرض نتائج ابني", type="primary")
        if ok:
            if blocked():
                st.error("محاولات كثيرة. انتظر دقائق ثم أعد المحاولة.")
            elif find_pin(p, load("students")):
                st.session_state.ppin = find_pin(p, load("students"))
                st.rerun()
            else:
                note_fail()
                st.error("الرمز غير صحيح. تأكد منه في رسالة الإدارة.")
        return
    stu = next((s for s in load("students") if s["pin"] == pin), None)
    if not stu:
        st.session_state.ppin = None
        st.rerun()
    sid = stu["id"]
    log_visit(sid)
    logs = by_date([l for l in load("logs") if l["sid"] == sid])
    att = by_date([a for a in load("att") if a["sid"] == sid])
    pay = sorted([p for p in load("pay") if p["sid"] == sid], key=lambda x: x["month"], reverse=True)
    mo = today()[:7]
    paid = any(p["month"] == mo for p in pay)

    st.markdown(
        f'<div class="stu"><span class="ln"></span><i class="med"></i><div class="nmx">{esc(stu["name"])}</div><i class="med"></i><span class="ln"></span></div>',
        unsafe_allow_html=True,
    )
    for a in sorted([x for x in load("ann") if not x["until"] or x["until"] >= today()], key=lambda x: x["date"], reverse=True)[:5]:
        st.markdown(f'<div class="note"><b>إعلان</b> ({esc(a["date"])}): {esc(a["text"])}</div>', unsafe_allow_html=True)
    try:
        _ww = week_winner(sk=SECKEY)
    except Exception:
        _ww = None
    if _ww and _ww["sid"]:
        _fn = first_name(stu["name"])
        if _ww["sid"] == sid:
            st.markdown(f'<div class="pay ok">🌟 مبارك! {esc(_fn)} هو طالب الأسبوع ({week_label(_ww["range"])}) لتحسّنه الملحوظ عن معدّله. بارك الله فيه.</div>', unsafe_allow_html=True)
            with st.expander("🎉 بطاقة طالب الأسبوع للمشاركة"):
                joy_card_ui(_fn, "طالب الأسبوع لتحسّنه الملحوظ", "week")
        elif cfg_get("honor") == "1":
            _w = next((r for r in _ww["rows"] if r["sid"] == _ww["sid"]), None)
            if _w:
                st.markdown(f'<div class="note">🌟 طالب الأسبوع ({week_label(_ww["range"])}): {esc(first_name(_w["name"]))}</div>', unsafe_allow_html=True)
    st.markdown(challenge_html(stu, now().strftime("%Y-%m"), [l for l in load("logs") if l["sid"] == sid], att, [d for d in load("disc") if d["sid"] == sid]), unsafe_allow_html=True)
    n_p, n_a, n_e = sum(a["status"] in ("p", "l") for a in att), sum(a["status"] == "a" for a in att), sum(a["status"] == "e" for a in att)
    st.markdown(
        f'<div class="trio"><div><b class="c-ok">{n_p}</b><span>حضور</span></div>'
        f'<div><b class="c-no">{n_a}</b><span>غياب</span></div>'
        f'<div><b class="c-ex">{n_e}</b><span>غياب بعذر</span></div></div>'
        + ('<div class="pay ok">غير معني بالاشتراك</div>' if stu.get("exempt") == "1" else
           f'<div class="pay ok">اشتراك شهر {mo} مسدَّد</div>' if paid else f'<div class="pay no">اشتراك شهر {mo} لم يُسدَّد بعد</div>'),
        unsafe_allow_html=True,
    )

    md = mdays_of(stu)
    if md and stu["grp"] in REV_SHEIKH:
        d2, k2 = next_hifz(md, MDAYS)
        when2 = "اليوم" if k2 == 0 else ("غدا" if k2 == 1 else f"يوم {MDAYS[next(x for x in md if MDAYS[x][1] == d2.weekday())][0]} {d2.strftime('%d/%m')}")
        st.markdown(
            f'<div class="pay ok">أيام المراجعة مع {REV_SHEIKH[stu["grp"]]}: {names_of(md, MDAYS)}<br>حصة المراجعة القادمة: {when2}</div>',
            unsafe_allow_html=True,
        )
    hd = days_of(stu)
    if hd:
        nm = " و".join(DAYS[k][0] for k in hd)
        d, k = next_hifz(hd)
        when = "اليوم" if k == 0 else ("غدا" if k == 1 else f"يوم {DAYS[next(x for x in hd if DAYS[x][1] == d.weekday())][0]} {d.strftime('%d/%m')}")
        st.markdown(
            f'<div class="pay ok">يوم الحفظ مع {DIR_N}: {nm}<br>حصة الحفظ القادمة: {when}</div>',
            unsafe_allow_html=True,
        )
    st.markdown(
        '<div class="note">ملاحظة لأولياء الأمور: نرجو متابعة ابنكم في المراجعة والورد اليومي والحفظ، '
        'فبذلك يكون التحصيل جيدا بإذن الله. ونؤكد على ضرورة عدم التغيب عن الحلقة القرآنية إلا بعذر.</div>',
        unsafe_allow_html=True,
    )

    _mon = {}
    for a in att:
        if a["status"] == "a":
            _mon[a["date"][:7]] = _mon.get(a["date"][:7], 0) + 1
    for _m, _n in sorted(((m_, n_) for m_, n_ in _mon.items() if n_ >= ALERT_ABS), reverse=True)[:3]:
        st.markdown(
            f'<div class="pay no">⛔ تجاوز ابنكم الحد المسموح به في الغياب: {_n} غيابات دون تبرير في شهر {month_label(_m)} (الحد {ALERT_ABS - 1}). '
            f'يلزم التقرب من المدرسة لتبرير الغياب.</div>', unsafe_allow_html=True)
    _rp = [m for m in load("msg") if m["sid"] == sid and m["who"] != "parent" and m["read"] != "1"]
    if _rp:
        _by = "، ".join(sorted({TKEY[m["who"]]["n"] for m in _rp if m["who"] in TKEY}))
        st.markdown(f'<div class="note">💬 لديكم {len(_rp)} رد جديد من {esc(_by) or "الشيخ"}. افتحوا تبويب «المراسلة» لقراءته.</div>', unsafe_allow_html=True)
    _ua = [a for a in att if a["status"] == "a"]
    if _ua:
        _ds = "، ".join(a["date"][8:10] + "/" + a["date"][5:7] for a in sorted(_ua, key=lambda a: a["date"], reverse=True)[:6])
        st.markdown(
            f'<div class="pay no">تنبيه: تغيّب ابنكم {len(_ua)} مرة دون تبرير ({_ds}). '
            f'نرجو تبرير الغياب من تبويب «الحضور»، أو التقرب من المدرسة إن استُنفد حد التبريرات.</div>',
            unsafe_allow_html=True,
        )

    pre_ui(stu, att)
    t1, t2, t3, t4, t5, t6 = st.tabs(["الحفظ", "المراجعة", "الحضور", "الاشتراك", "التقرير", "المراسلة"])
    with t1:
        hl = [l for l in logs if l["type"] == "hifz"]
        st.markdown(progress_html(hl), unsafe_allow_html=True)
        st.markdown(quran_map_html(logs), unsafe_allow_html=True)
        for _e in joy_events(logs)[:2]:
            with st.expander(f"🎉 بطاقة فرحة: {_e['line1']}"):
                joy_card_ui(first_name(stu["name"]), _e["line1"], f"s{_e['date']}{_e['line1']}")
        parent_target_ui(stu)
        st.caption("يُحتسب في التقدم المقطع الجديد فقط، أما التكرار والإعادة القديمة فللتثبيت.")
        st.markdown(logs_html(by_date(hl), "لم يُسجَّل حفظ بعد."), unsafe_allow_html=True)
    with t2:
        _pt = err_top(logs, sid, 5, 60)
        if _pt:
            st.markdown(f'<div class="note"><b>آيات تحتاج تثبيتا</b> (تعثّر فيها ابنكم مؤخرا): {esc(err_top_text(_pt))}</div>', unsafe_allow_html=True)
        st.markdown(logs_html([l for l in logs if l["type"] != "hifz"], "لم تُسجَّل مراجعة بعد."), unsafe_allow_html=True)
    with t3:
        AC = {"p": "g1", "l": "g3", "a": "g5", "e": "g4"}
        used = {}
        for a in att:
            if a.get("by") == "parent":
                used[a["date"][:7]] = used.get(a["date"][:7], 0) + 1
        absent = [a for a in att if a["status"] == "a"]
        if absent:
            sec("تبرير الغياب")
            st.markdown(
                f'<div class="note">يمكنكم تبرير ما يصل إلى {MAX_JUST} غيابات في الشهر الواحد من هنا. '
                f'عند تجاوز هذا الحد يلزم التقرب من المدرسة لتبرير الغياب. '
                f'تبريرات شهر {mo}: {used.get(mo, 0)} من {MAX_JUST}.</div>',
                unsafe_allow_html=True,
            )
            for a in absent[:20]:
                m = a["date"][:7]
                if used.get(m, 0) >= MAX_JUST:
                    st.markdown(
                        f'<div class="pay no">غياب {esc(a["date"])}: استُنفد حد التبريرات لشهر {esc(m)}، '
                        f'يرجى التقرب من المدرسة لتبريره.</div>',
                        unsafe_allow_html=True,
                    )
                    continue
                with st.expander(f"تبرير غياب {a['date']}"):
                    why = st.text_input("سبب الغياب", key=f"why{a['id']}", max_chars=120)
                    if st.button("تبرير الغياب", key=f"jb{a['id']}", type="primary"):
                        if not why.strip():
                            st.error("اكتب سبب الغياب")
                        else:
                            _load.clear()
                            fresh = [x for x in load("att") if x["sid"] == sid]
                            n_now = sum(1 for x in fresh if x.get("by") == "parent" and x["date"][:7] == m)
                            tgt = next((x for x in fresh if x["id"] == a["id"]), None)
                            if not tgt or tgt["status"] != "a":
                                st.error("تغيّرت حالة هذا الغياب، أعد تحميل الصفحة.")
                            elif n_now >= MAX_JUST:
                                st.error("استُنفد حد التبريرات لهذا الشهر، يرجى التقرب من المدرسة.")
                            else:
                                write(STORE.update, "att", a["id"], {"status": "e", "why": why.strip(), "by": "parent"})
                                audit("تبرير غياب بواسطة الولي", f"{stu['name']} · {a['date']} · {why.strip()}", by="ولي الأمر")
                                st.rerun()
            sec("سجل الحضور")
        st.markdown(
            "".join(
                f'<div class="ent"><i class="med"></i><div class="bd2"><div class="txt">{esc(a["date"])}</div>'
                + (f'<div class="meta"><span>بتبرير الولي: {esc(a.get("why", ""))}</span></div>' if a.get("by") == "parent" else "")
                + '</div>'
                f'<span class="gr {AC.get(a["status"], "g3")}">{ATT.get(a["status"], esc(a["status"]))}</span></div>'
                for a in att[:40]
            )
            or '<div class="empty">لا يوجد تسجيل حضور بعد.</div>',
            unsafe_allow_html=True,
        )
    with t4:
        st.markdown(
            "".join(
                f'<div class="ent"><i class="med"></i><div class="bd2"><div class="txt">شهر {esc(p["month"])}</div>'
                f'<div class="meta"><span>{esc(p["amount"])}</span><span>{esc(p["date"])}</span></div></div>'
                f'<span class="gr g1">مسدَّد</span></div>'
                for p in pay
            )
            or ('<div class="empty">هذا الطالب غير معني بالاشتراك.</div>' if stu.get("exempt") == "1" else '<div class="empty">لا توجد دفعات مسجّلة بعد.</div>'),
            unsafe_allow_html=True,
        )
    with t5:
        curve_ui(sid)
        mo5 = st.selectbox("الشهر", recent_months(), format_func=month_label, key="pm_sel")
        S5, rk5, tot5 = month_bundle(mo5)
        v5 = S5.get(sid)
        if v5 and v5["has"]:
            st.markdown(
                f'<div class="trio"><div><b class="c-ok">{"—" if v5["dis"] is None else f"{v5["dis"]:.2f}"}</b><span>الانضباط من 3</span></div>'
                f'<div><b class="c-ok">{"—" if v5["pct"] is None else f"{v5["pct"]:g}%"}</b><span>نسبة الحضور</span></div>'
                f'<div><b class="c-ex">{rk5.get(sid, "—")}</b><span>الترتيب من {tot5}</span></div></div>',
                unsafe_allow_html=True,
            )
            if v5.get("badges"):
                st.markdown('<div class="pay ok">' + "<br>".join(f"{ic} وسام: {esc(tx)}" for ic, tx in v5["badges"]) + "</div>", unsafe_allow_html=True)
                _done = month_ending(mo5)
                for _ic, _tx in [b_ for b_ in v5["badges"] if _done or b_[0] == "🎓"][:4]:
                    with st.expander(f"🎉 بطاقة فرحة: {_tx}"):
                        joy_card_ui(first_name(stu["name"]), badge_line(_tx), f"b{mo5}{_tx}")
            if month_ending(mo5):
                st.markdown(compare_html(v5), unsafe_allow_html=True)
            else:
                st.markdown('<div class="note"><b>مقارنة بالشهر السابق</b><div class="meta">تظهر هنا في آخر أسبوع من الشهر، بعد اكتمال نتائجه.</div></div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="empty">لا توجد بيانات لهذا الشهر بعد.</div>', unsafe_allow_html=True)
        sec("الاختبارات")
        st.markdown(exams_html(sid), unsafe_allow_html=True)
        if cfg_get("honor") == "1" and tot5 >= 3:
            top = sorted([(rk5[x["id"]], x["name"]) for x in load("students") if x["id"] in rk5 and rk5[x["id"]] <= 3])
            if top:
                st.markdown(
                    f'<div class="pay ok">الأوائل في شهر {month_label(mo5)}: ' + "، ".join(esc(n) for _, n in top) + "</div>",
                    unsafe_allow_html=True,
                )
        monthly_ui(stu, "p")
    with t6:
        parent_msgs_tab(stu)
    st.markdown('<div class="foot">بارك الله فيكم وفي أبنائكم</div>', unsafe_allow_html=True)
    if st.button("خروج"):
        st.session_state.ppin = None
        st.rerun()


# ───────────────────────── صفحة المشايخ ─────────────────────────
def _section_users(cfg):
    if str(cfg.get("solo", "")).strip() in ("1", "true", "yes"):
        return [str(cfg.get("user0", "")).lower()]
    return [str(cfg.get(k, "")).lower() for k in ("user0", "user1", "user2")]


def _find_user(u):
    """وضع الأقسام المتعددة: القسم الذي ينتمي إليه اسم المستخدم، ومكانه بين شيوخه."""
    for key, cfg in SECS.items():
        us = _section_users(cfg)
        if u and u in us:
            return key, us.index(u)
    return None, None


def _hashes_for(key):
    cfg = SECS[key]
    base = _OSAMA_HASHES if str(cfg.get("seeded", "")).strip() in ("1", "true", "yes") else {}
    try:
        return {**base, **{str(k).lower(): v for k, v in dict(st.secrets["staff"]).items()}}
    except Exception:
        return dict(base)


def login_view():
    header("تسجيل دخول المشايخ", basmala=True)
    with st.form("lf"):
        u = st.text_input("اسم المستخدم").strip().lower()
        p = st.text_input("الرمز السري", type="password").strip()
        ok = st.form_submit_button("دخول", type="primary")
    if ok:
        if blocked():
            st.error("محاولات كثيرة، حاول بعد قليل.")
            return
        if MULTI:
            key, i = _find_user(u)
            if key and sha(u, p) == _hashes_for(key).get(u):
                st.session_state.sec_key = key
                st.session_state.me = i
                st.rerun()
            note_fail()
            st.error("اسم المستخدم أو الرمز السري غير صحيح")
            return
        i = next((k for k, t in enumerate(TEACHERS) if t["u"] == u), None)
        if i is not None and sha(u, p) == staff_hashes()[u]:
            st.session_state.me = i
            st.rerun()
        else:
            note_fail()
            st.error("اسم المستخدم أو الرمز السري غير صحيح")


def mine(s, i):
    return i == 0 or s["grp"] == str(i)


def start_of(per):
    d = now().date()
    if per == "week":
        d -= dt.timedelta(days=(d.weekday() - WEEK_START) % 7)
    if per == "month":
        d = d.replace(day=1)
    return d.isoformat()


def report_tab(i):
    students, logs = load("students"), load("logs")
    per = st.radio("الفترة", ["اليوم", "هذا الأسبوع", "هذا الشهر"], horizontal=True)
    st_ = start_of({"اليوم": "day", "هذا الأسبوع": "week", "هذا الشهر": "month"}[per])
    inp = [l for l in logs if st_ <= l["date"] <= today()]
    if not students:
        st.info("أضف الطلبة لتظهر النسب.")
        return
    sec("نسبة إنجاز المشايخ")
    for k, t in enumerate(TEACHERS):
        if t.get("alias"):
            continue
        done = {l["sid"] for l in inp if l["teacher"] == t["n"]}
        m = [s for s in students if mine(s, k)]
        n = sum(s["id"] in done for s in m)
        pc = round(n * 100 / len(m)) if m else 0
        st.markdown(
            f'<div class="rep"><div class="top"><div class="nm">{t["n"]}<span class="chip">{t["r"]}</span></div>'
            f'<div class="pc">{pc}<small>%</small></div></div>'
            f'<div class="bar"><i style="width:{pc}%"></i></div><div class="sub">{n} من {len(m)} طالب</div></div>',
            unsafe_allow_html=True,
        )
        miss = [s["name"] for s in m if s["id"] not in done]
        if miss:
            with st.expander(f"لم يُسجَّل لهم ({len(miss)})"):
                st.write("، ".join(miss))


def student_tab(i):
    me = TEACHERS[i]
    admin = me.get("admin")
    students = sorted(load("students"), key=lambda s: s["name"])
    vis = students if admin else [s for s in students if mine(s, i)]
    if not vis:
        st.info("لا يوجد طلبة بعد. أضفهم من تبويب الإدارة.")
        return
    q = st.text_input("بحث عن طالب")
    vis = [s for s in vis if q in s["name"]] if q else vis
    if not vis:
        st.caption("لا نتائج.")
        return
    _by = {x["id"]: x for x in vis}
    sid = st.selectbox("الطالب", list(_by), format_func=lambda k: _by[k]["name"] + (f"  ·  م{_by[k]['grp']}" if _by[k]["grp"] else ""), key="stu_sel")
    s = next((x for x in students if x["id"] == sid), _by[sid])
    _last, _n_mo, _n_all = visit_info(sid)
    st.caption(f"آخر زيارة للولي: {_last} · زياراته هذا الشهر: {_n_mo}" if _last else "لم يزر الولي صفحة ابنه بعد.")  # نسخة حديثة من بيانات الطالب (اختيار القائمة قد يحمل نسخة قديمة)

    if admin:
        with st.expander("تعديل اسم الطالب"):
            with st.form(f"rn{sid}"):
                nn = st.text_input("الاسم الصحيح", value=s["name"], max_chars=80, key=f"rnv{sid}_{s['name']}")
                if st.form_submit_button("حفظ الاسم"):
                    nn = " ".join(nn.split())
                    if len(nn) < 2:
                        st.error("اكتب اسما صحيحا.")
                    elif nn == s["name"]:
                        st.info("لم يتغير الاسم.")
                    elif any(x["name"] == nn and x["id"] != sid for x in students):
                        st.error("يوجد طالب بهذا الاسم، أضف ما يميّزه (مثل اسم الأب).")
                    else:
                        write(STORE.update, "students", sid, {"name": nn})
                        audit("تعديل اسم طالب", f"{s['name']} ← {nn}")
                        st.toast("✓ تم تعديل الاسم")
                        st.rerun()

    is_h = me["t"] == "hifz"
    sec("تسجيل الحفظ" if is_h else "تسجيل المراجعة")
    my_logs = [l for l in load("logs") if l["sid"] == sid]
    if is_h:
        last = next((l for l in by_date([x for x in my_logs if x["type"] == "hifz" and aya_set(x)])), None)
        d_sur, d_a1 = 114, 1
        if last:
            d_sur, d_a1 = int(last["sur"]), int(last["a2"]) + 1
            if d_a1 > SURAHS[d_sur - 1][1]:  # أتمّ السورة: ننتقل إلى التي قبلها (الحفظ من آخر المصحف)
                d_sur, d_a1 = max(d_sur - 1, 1), 1
        nl = len(my_logs)
        sn = st.selectbox("السورة", list(range(1, 115)), index=d_sur - 1, format_func=lambda i: f"{i}. {SURAHS[i - 1][0]} ({SURAHS[i - 1][1]} آية)", key=f"hs{sid}_{nl}")
        na = SURAHS[sn - 1][1]
        en = st.selectbox("إلى سورة (اتركها «نفس السورة» إن كان التسجيل في سورة واحدة)", [0] + list(range(1, 115)),
                          format_func=lambda i: "نفس السورة" if i == 0 else f"{i}. {SURAHS[i - 1][0]}", key=f"he{sid}_{nl}_{sn}")
        nb = SURAHS[en - 1][1] if en else na
    else:
        nl = len(my_logs)
        st.markdown(review_status_html(sid, my_logs, now().date().isoformat()) or '<div class="empty">لا حفظ مرتبط بالسور بعد، فلا اقتراح للمراجعة.</div>', unsafe_allow_html=True)
        _rec = recent_hifz(sid, my_logs, now().date().isoformat())
        sn = st.selectbox("السورة التي روجعت", [0] + list(range(1, 115)), index=(_rec[0][0] if _rec else 0),
                          format_func=lambda i: "نص حر (بدون تحديد سورة)" if i == 0 else f"{i}. {SURAHS[i - 1][0]} ({SURAHS[i - 1][1]} آية)", key=f"ms{sid}_{nl}")
        na = SURAHS[sn - 1][1] if sn else 1
        en = 0
        if sn:
            en = st.selectbox("إلى سورة (اتركها «نفس السورة» إن كان التسجيل في سورة واحدة)", [0] + list(range(1, 115)),
                              format_func=lambda i: "نفس السورة" if i == 0 else f"{i}. {SURAHS[i - 1][0]}", key=f"me{sid}_{nl}_{sn}")
        nb = SURAHS[en - 1][1] if en else na
    if sn and (not en or en == sn):
        _pe = err_counts(my_logs, None, _ago(today(), 120))
        _pe = {p: v for p, v in _pe.items() if p[0] == sn}
        if _pe:
            st.info("تذكير: سبق أن تعثّر الطالب في هذه السورة عند: " + err_hint(my_logs, sid, set(_pe)))
    with st.form(f"lg{sid}", clear_on_submit=True):
        if is_h:
            kind = st.selectbox("نوع الحفظ", list(HK), format_func=HK.get)
            st.caption("إن لم يحفظ الطالب في هذه الحلقة فاختر التقدير «لم يحفظ» ولا تهتم بالآيات.")
            c1, c2 = st.columns(2)
            a1 = c1.number_input("من الآية", min_value=1, max_value=na, value=min(d_a1, na) if sn == d_sur else 1, step=1, key=f"ha1_{sid}_{sn}_{nl}")
            a2 = c2.number_input("إلى الآية" + (" (في السورة الأخيرة)" if en else ""), min_value=1, max_value=nb, value=nb, step=1, key=f"ha2_{sid}_{sn}_{en}_{nl}")
            detail = st.text_input("تفاصيل إضافية (اختياري)")
            err_in = st.text_input("آيات التعثّر (اختياري: أرقام مفصولة بفاصلة)")
        elif sn:
            _r0 = next((r for r in (_rec if sn else []) if r[0] == sn), None)
            c1, c2 = st.columns(2)
            a1 = c1.number_input("من الآية", min_value=1, max_value=na, value=_r0[1] if _r0 else 1, step=1, key=f"ma1_{sid}_{sn}_{nl}")
            a2 = c2.number_input("إلى الآية" + (" (في السورة الأخيرة)" if en else ""), min_value=1, max_value=nb, value=nb if en else (_r0[2] if _r0 else na), step=1, key=f"ma2_{sid}_{sn}_{en}_{nl}")
            detail = st.text_input("تفاصيل إضافية (اختياري)")
            err_in = st.text_input("آيات التعثّر (اختياري: أرقام مفصولة بفاصلة)")
        else:
            detail = st.text_input("ما تمت مراجعته (نص حر)")
            err_in = ""
        c1, c2 = st.columns(2)
        grade = c1.selectbox("التقدير", GRADES_H if is_h else GRADES)
        d = c2.date_input("التاريخ", value=now().date())
        note = st.text_input("ملاحظة" if is_h else "المطلوب إعادته والأخطاء (أي سورة ليست جيدة يعيدها، وما أخطاؤه)")
        if st.form_submit_button("حفظ التسجيل", type="primary"):
            none_ = is_h and grade == "لم يحفظ"
            if not none_ and (is_h or sn) and not en and a1 > a2:
                st.error("رقم آية البداية أكبر من آية النهاية")
            elif not is_h and not sn and not detail.strip():
                st.error("اكتب ما تمت مراجعته")
            elif not none_ and (is_h or sn) and parse_err(err_in, sn, int(a1), int(a2), en)[1]:
                st.error(parse_err(err_in, sn, int(a1), int(a2), en)[1])
            else:
                base = {"sid": sid, "date": d.isoformat(), "teacher": me["n"], "role": me["r"], "type": "hifz" if is_h else "mur",
                        "grade": grade, "note": note.strip(), "kind": kind if is_h else "", "ts": str(int(time.time() * 1000))}
                ex = f" — {detail.strip()}" if detail.strip() else ""
                if none_:
                    rows = [{**base, "kind": "none", "detail": "لم يحفظ في هذه الحلقة"}]
                    shown = "لم يحفظ"
                elif is_h or sn:
                    pre = "" if is_h else "مراجعة "
                    shown = seg_text(segments(sn, int(a1), en or sn, int(a2)), pre)
                    _es = parse_err(err_in, sn, int(a1), int(a2), en)[0]
                    if not en or en == sn:
                        _hint = err_hint(my_logs, sid, {(sn, k_) for k_ in range(int(a1), int(a2) + 1)})
                        if _hint:
                            flash_add(f"تنبيه ({s['name']}): سبق أن تعثّر في هذا المقطع عند: {_hint}. راجع أخطاءه فيه.")
                    rows = [{**base, "sur": str(sn), "a1": str(int(a1)), "a2": str(int(a2)), "sur2": str(en) if en and en != sn else "", "err": _es, "detail": shown + ex}]
                else:
                    rows = [{**base, "detail": detail.strip()}]
                    shown = detail.strip()
                try:
                    ids = write(STORE.add_many, "logs", rows)
                except Exception as e:
                    ids = None
                    st.error(f"تعذّر الحفظ في الجدول: {explain(e)}")
                have = {x["id"] for x in load("logs")} if ids else set()
                if ids and not all(k in have for k in ids):
                    st.error("لم يُحفَظ التسجيل في الجدول! أعد المحاولة، وإن تكرر الأمر فاضغط «فحص التخزين» في تبويب الإدارة وأرسل نتيجته.")
                elif ids:
                    audit("تسجيل حفظ" if is_h else "تسجيل مراجعة", f"{s['name']}: {shown} ({grade})")
                    st.toast("✓ تم حفظ التسجيل")
                    st.rerun()

    if is_h or admin:
        sec("تقدم الحفظ")
        st.markdown(progress_html([l for l in my_logs if l["type"] == "hifz"]), unsafe_allow_html=True)
        st.markdown(quran_map_html(my_logs), unsafe_allow_html=True)

    sec("الاختبارات")
    _exs = load("exams")
    for h_ in hizb_candidates(sid, my_logs, _exs):
        st.markdown(f'<div class="note">🎓 أتمّ حفظ {esc(hizb_label(h_))}: يُقترح امتحانه فيه من أوله إلى آخره.</div>', unsafe_allow_html=True)
    with st.form(f"exf{sid}", clear_on_submit=True):
        c1, c2 = st.columns(2)
        ek = c1.selectbox("نوع الاختبار", EXAM_KINDS)
        ep = c2.number_input("رقم الحزب (لاختبار الحزب)", min_value=1, max_value=60, value=(hizb_candidates(sid, my_logs, _exs) or [1])[0], step=1)
        c3, c4 = st.columns(2)
        es = c3.number_input("العلامة من 20", min_value=0.0, max_value=20.0, value=10.0, step=0.5)
        ed = c4.date_input("التاريخ", value=now().date(), key=f"exd{sid}")
        en_ = st.text_input("ملاحظة (اختياري)", key=f"exn{sid}")
        if st.form_submit_button("تسجيل الاختبار", type="primary"):
            write(STORE.add, "exams", {"sid": sid, "date": ed.isoformat(), "kind": ek, "part": str(int(ep)) if ek == "اختبار حزب" else "", "score": str(es), "note": en_.strip(), "teacher": me["n"]})
            audit("تسجيل اختبار", f"{s['name']}: {ek}{' ' + str(int(ep)) if ek == 'اختبار حزب' else ''} = {es:g}/20")
            st.toast("✓ سُجّل الاختبار")
            st.rerun()
    for e_ in sorted([e for e in _exs if e["sid"] == sid], key=lambda e: e["date"], reverse=True)[:8]:
        c1, c2 = st.columns([5, 1])
        c1.caption(f"{e_['date']} · {e_['kind']}" + (f" {e_['part']}" if e_["part"] else "") + f" · {num(e_['score']):g}/20 · {e_['teacher']}" + (f" · {e_['note']}" if e_["note"] else ""))
        if (admin or e_["teacher"] == me["n"]) and c2.button("حذف", key=f"dx{e_['id']}"):
            write(STORE.delete, "exams", e_["id"])
            audit("حذف اختبار", s["name"])
            st.rerun()

    sec("الحضور والغياب")
    day = st.date_input("اليوم", value=now().date(), key=f"ad{sid}").isoformat()
    cur = next((a for a in load("att") if a["sid"] == sid and a["date"] == day), None)
    keys = list(ATT)
    ch = st.radio("الحضور", keys, format_func=ATT.get, horizontal=True,
                  index=keys.index(cur["status"]) if cur and cur["status"] in keys else None,
                  key=f"att{sid}_{day}_{cur['status'] if cur else ''}", label_visibility="collapsed")
    c1, c2 = st.columns(2)
    if c1.button("حفظ الحضور", key=f"sa{sid}") and ch:
        if cur:
            write(STORE.update, "att", cur["id"], {"status": ch, "teacher": me["n"]})
        else:
            write(STORE.add, "att", {"sid": sid, "date": day, "status": ch, "teacher": me["n"]})
        audit("تسجيل حضور", f"{s['name']} · {day} · {ATT[ch]}")
        st.success("✓ تم تسجيل الحضور")
        st.rerun()
    if cur and cur.get("by") == "parent":
        st.caption(f"بتبرير الولي، السبب: {cur.get('why', '')}")
    if cur and c2.button("حذف تسجيل هذا اليوم", key=f"da{sid}"):
        write(STORE.delete, "att", cur["id"])
        audit("حذف حضور", f"{s['name']} · {day}")
        st.rerun()
    a_all = [a for a in load("att") if a["sid"] == sid]
    st.caption(f"حضور: {sum(a['status'] in ('p', 'l') for a in a_all)} (متأخر: {sum(a['status'] == 'l' for a in a_all)}) · غياب: {sum(a['status'] in ('a', 'e') for a in a_all)}")

    pm = sorted(p["month"] for p in load("pay") if p["sid"] == sid)
    sec("الاشتراك")
    if s.get("exempt") == "1":
        st.caption("هذا الطالب غير معني بالاشتراك.")
    else:
        st.caption("المسدَّد: " + ("، ".join(pm) if pm else "لا شيء"))
    if admin:
        ex = st.checkbox("غير معني بالاشتراك (معفى)", value=s.get("exempt") == "1", key=f"ex{sid}_{s.get('exempt', '')}")
        if ex != (s.get("exempt") == "1"):
            write(STORE.update, "students", sid, {"exempt": "1" if ex else ""})
            audit("إعفاء من الاشتراك" if ex else "إلغاء الإعفاء", s["name"])
            st.rerun()
        if s.get("pstatus") == "pending":
            st.caption(f"اقتراح الولي: {('الوصول إلى سورة ' + SURAHS[int(s['psur']) - 1][0] + ' — ') if str(s.get('psur', '')).isdigit() and 1 <= int(s['psur']) <= 114 else ''}≈ {s.get('ptarget', '')} آية في الشهر (اعتمده من «حلقة اليوم»، أو حدّد هدفا آخر هنا).")
        with st.form(f"tg{sid}"):
            tv = st.number_input("هدف الحفظ الشهري لهذا الطالب (آيات) — صفر يعني الهدف العام", min_value=0, max_value=600, value=int(num(s.get("target"))), step=5, key=f"tgv{sid}")
            if st.form_submit_button("حفظ هدف الطالب"):
                write(STORE.update, "students", sid, {"target": str(int(tv)) if tv else "", **({"pstatus": "set"} if s.get("pstatus") == "pending" else {})})
                audit("هدف حفظ فردي", f"{s['name']}: {int(tv) or 'العام'}")
                st.rerun()
        with st.form(f"pay{sid}", clear_on_submit=True):
            c1, c2 = st.columns(2)
            mo = c1.text_input("الشهر (YYYY-MM)", value=today()[:7])
            am = c2.text_input("المبلغ")
            if st.form_submit_button("تسجيل الدفع"):
                if mo in pm:
                    st.error("هذا الشهر مسدَّد مسبقاً")
                elif not am.strip():
                    st.error("أدخل المبلغ")
                else:
                    write(STORE.add, "pay", {"sid": sid, "month": mo, "amount": am.strip(), "date": today(), "teacher": me["n"]})
                    audit("تسجيل دفع", f"{s['name']} · {mo} · {am.strip()}")
                    st.success("✓ تم تسجيل الدفع")
        pays = sorted([p for p in load("pay") if p["sid"] == sid], key=lambda p: p["month"], reverse=True)
        if pays:
            pp = st.selectbox("دفعة مسجّلة", pays, format_func=lambda p: f"{p['month']} — {p['amount']}", key=f"pp{sid}")
            if st.button("حذف الدفعة المحددة", key=f"dp{sid}"):
                write(STORE.delete, "pay", pp["id"])
                audit("حذف دفعة", f"{s['name']} · {pp['month']} · {pp['amount']}")
                st.rerun()
        g = (s["grp"] or "") if SOLO else st.selectbox("توجيه الطالب للمراجعة عند", ["", "1", "2"], index=["", "1", "2"].index(s["grp"] or ""),
                         format_func=lambda x: {"": "لم يُوجَّه بعد", "1": f"{REV1_N} (مراجعة 1)", "2": f"{REV2_N} (مراجعة 2)"}[x],
                         key=f"g{sid}_{s['grp']}")
        if g != (s["grp"] or ""):
            write(STORE.update, "students", sid, {"grp": g})
            audit("توجيه للمراجعة", f"{s['name']} ← {g or 'بدون'}")
            st.rerun()
        dsel = st.multiselect(f"أيام الحفظ مع {DIR_N}", list(DAYS), default=days_of(s),
                              format_func=lambda k: DAYS[k][0], key=f"d{sid}_{s['days']}")
        if ",".join(dsel) != ",".join(days_of(s)):
            write(STORE.update, "students", sid, {"days": ",".join(dsel)})
            audit("أيام الحفظ", f"{s['name']} ← {','.join(dsel) or 'بدون'}")
            st.rerun()
        msel = st.multiselect("أيام المراجعة", list(MDAYS), default=mdays_of(s), format_func=lambda k: MDAYS[k][0], key=f"md{sid}_{s['mdays']}")
        if ",".join(msel) != ",".join(mdays_of(s)):
            write(STORE.update, "students", sid, {"mdays": ",".join(msel)})
            audit("أيام المراجعة", f"{s['name']} ← {','.join(msel) or 'بدون'}")
            st.rerun()
        if s["pin"]:
            app = secret("app_url", "")
            st.caption("رمز الولي (اضغط أيقونة النسخ على يمين الرمز):")
            st.code(s["pin"], language=None)
            msg = (f"السلام عليكم ورحمة الله،\nولي أمر الطالب {s['name']}\nرابط متابعة ابنكم في {ASSOC} "
                   f"(يفتح مباشرة دون الحاجة إلى الرمز):\n{app_link()}&k={s['pin']}\n"
                   f"وإن طُلب منكم الرمز فهو: {s['pin']}")
            st.link_button("إرسال لولي الأمر عبر واتساب", "https://wa.me/?text=" + urllib.parse.quote(msg))
        else:
            st.caption("لا يوجد رمز للولي — من تبويب الإدارة اضغط «توليد رموز الأولياء».")

    sec("التقرير الشهري (PDF)")
    monthly_ui(s, f"s{sid}", staff=True)

    sec("السجل")
    L = by_date([l for l in load("logs") if l["sid"] == sid])
    if not L:
        st.caption("لا توجد تسجيلات.")
    allv = st.checkbox("عرض كل السجل", key=f"all{sid}") if len(L) > 12 else True
    for l in (L if allv else L[:12]):
        with st.expander(f"{l['role'] or '-'} · {l['detail'][:35]} · {l['date']}"):
            st.caption(f"سجّله: {l['teacher']}")
            if not (admin or l["type"] == me["t"]):
                st.caption("هذا التسجيل لشيخ آخر، ولا يمكنك تعديله.")
                continue
            try:
                d0 = dt.date.fromisoformat(l["date"])
            except ValueError:
                d0 = now().date()
            with st.form(f"el{l['id']}"):
                has_s = bool(aya_set(l))
                has_span = bool(l.get("sur2")) and l.get("sur2") != l.get("sur")
                kd2 = None
                if l["type"] == "hifz" and l.get("kind", "") != "none":
                    kd2 = st.selectbox("نوع الحفظ", list(HK), index=list(HK).index(l.get("kind")) if l.get("kind") in HK else 0, format_func=HK.get, key=f"ek{l['id']}")
                if has_span:
                    st.caption(l["detail"].split(" — ", 1)[0] + " (المدى بين سورتين لا يُعدَّل، احذف التسجيل وأعد إدخاله إن أخطأت)")
                    dd = st.text_input("تفاصيل إضافية", value=l["detail"].split(" — ", 1)[1] if " — " in l["detail"] else "")
                elif has_s:
                    ca, cb = st.columns(2)
                    ea1 = ca.number_input("من الآية", min_value=1, max_value=SURAHS[int(l["sur"]) - 1][1], value=int(l["a1"]), step=1, key=f"ea1{l['id']}")
                    ea2 = cb.number_input("إلى الآية", min_value=1, max_value=SURAHS[int(l["sur"]) - 1][1], value=int(l["a2"]), step=1, key=f"ea2{l['id']}")
                    dd = st.text_input("تفاصيل إضافية", value=l["detail"].split(" — ", 1)[1] if " — " in l["detail"] else "")
                    ee = st.text_input("آيات التعثّر (أرقام مفصولة بفاصلة)", value="، ".join(str(k_) for _, k_ in err_pairs(l)), key=f"eer{l['id']}")
                else:
                    dd = st.text_input("ما تم", value=l["detail"])
                c1, c2 = st.columns(2)
                _gl = GRADES_H if l["type"] == "hifz" else GRADES
                gr = c1.selectbox("التقدير", _gl, index=_gl.index(l["grade"]) if l["grade"] in _gl else 0)
                dte = c2.date_input("التاريخ", value=d0)
                nt = st.text_input("ملاحظة", value=l["note"])
                b1, b2 = st.columns(2)
                save = b1.form_submit_button("حفظ التعديل", type="primary")
                dele = b2.form_submit_button("حذف التسجيل")
            if save:
                if has_span:
                    ch = {"detail": l["detail"].split(" — ", 1)[0] + (f" — {dd.strip()}" if dd.strip() else "")}
                elif has_s:
                    if ea1 > ea2:
                        st.error("رقم آية البداية أكبر من آية النهاية")
                        continue
                    es_, em_ = parse_err(ee, int(l["sur"]), int(ea1), int(ea2))
                    if em_:
                        st.error(em_)
                        continue
                    ch = {"a1": str(int(ea1)), "a2": str(int(ea2)), "err": es_,
                          "detail": f"سورة {SURAHS[int(l['sur']) - 1][0]} من الآية {int(ea1)} إلى الآية {int(ea2)}" + (f" — {dd.strip()}" if dd.strip() else "")}
                else:
                    ch = {"detail": dd.strip()}
                write(STORE.update, "logs", l["id"], {**ch, "grade": gr, "date": dte.isoformat(), "note": nt.strip(), **({"kind": kd2} if kd2 else {})})
                audit("تعديل تسجيل", f"{s['name']}: {l['detail']} ← {ch['detail']}")
                st.rerun()
            if dele:
                write(STORE.delete, "logs", l["id"])
                audit("حذف تسجيل", f"{s['name']}: {l['detail']} ({l['date']})")
                st.rerun()


def distribute_by_records(students, logs):
    """يوزّع حسب آخر مراجعة سُجّلت للطالب (مراجعة 1 أو 2)، والباقي بالتساوي بين المجموعتين."""
    last = {}
    for l in sorted(logs, key=lambda x: (x["date"], x["ts"])):
        if l["type"] == "mur" and l["role"] in ("مراجعة 1", "مراجعة 2"):
            last[l["sid"]] = "1" if l["role"] == "مراجعة 1" else "2"
    res, cnt = {}, {"1": 0, "2": 0}
    for s in students:
        if s["id"] in last:
            res[s["id"]] = last[s["id"]]
            cnt[last[s["id"]]] += 1
    for s in students:
        if s["id"] not in res:
            g = "1" if cnt["1"] <= cnt["2"] else "2"
            res[s["id"]] = g
            cnt[g] += 1
    return res


ORD_AR = {1: "الأولى", 2: "الثانية", 3: "الثالثة", 4: "الرابعة", 5: "الخامسة"}


def cert_pdf(items):
    """شهادات تقدير بالعرض: صفحة لكل (اسم، سطر السبب، سطر الدعاء)."""
    from reportlab.lib.colors import HexColor, white
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfgen import canvas

    if not os.path.exists(FONT):
        raise RuntimeError("ملف الخط Amiri-Regular.ttf غير موجود في GitHub بجانب app.py")
    if "Amiri" not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont("Amiri", FONT))
    INK, GOLD, PAPER, MUT = HexColor("#0a4a3e"), HexColor("#a9822a"), HexColor("#fbf8ec"), HexColor("#5f6f67")
    W, H = landscape(A4)
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(W, H))
    c.setTitle("شهادة تقدير")
    d = now()
    date_txt = f"{CITY}، في {d.day} {MONTHS_AR[d.month - 1]} {d.year}"

    def put(x, y, t, size, color=INK):
        c.setFont("Amiri", size)
        c.setFillColor(color)
        c.drawCentredString(x, y, _shape(str(t)))

    def fit(t, size, maxw):
        while c.stringWidth(_shape(str(t)), "Amiri", size) > maxw and size > 10:
            size -= 1
        return size

    for name, reason, dua in items:
        c.setFillColor(PAPER)
        c.rect(0, 0, W, H, stroke=0, fill=1)
        c.setStrokeColor(INK)
        c.setLineWidth(5)
        c.rect(18, 18, W - 36, H - 36, stroke=1, fill=0)
        c.setStrokeColor(GOLD)
        c.setLineWidth(1.6)
        c.rect(30, 30, W - 60, H - 60, stroke=1, fill=0)
        c.setFillColor(GOLD)
        for cx, cy in ((30, 30), (W - 30, 30), (30, H - 30), (W - 30, H - 30)):
            c.circle(cx, cy, 7, stroke=0, fill=1)
        lp = os.path.join(HERE, "logo.jpg")
        if os.path.exists(lp):
            c.drawImage(lp, W / 2 - 29, H - 112, 58, 58, preserveAspectRatio=True, mask="auto")
        put(W / 2, H - 46, "بسم الله الرحمن الرحيم", 17, GOLD)
        put(W / 2, H - 148, "شهادة تقدير", 44, INK)
        c.setStrokeColor(GOLD)
        c.setLineWidth(1.2)
        c.line(W / 2 - 130, H - 162, W / 2 + 130, H - 162)
        put(W / 2, H - 200, f"تتشرف {ASSOC} – {SEC} بمنح هذه الشهادة للطالب", 17, MUT)
        put(W / 2, H - 258, name, fit(name, 40, W - 160), INK)
        put(W / 2, H - 305, reason, fit(reason, 22, W - 160), INK)
        put(W / 2, H - 340, dua, fit(dua, 17, W - 160), MUT)
        put(W / 2, 92, date_txt, 14, MUT)
        put(W - 150, 92, "إدارة الجمعية", 15, INK)
        put(150, 92, f"مدير القسم: {DIR_N}", 15, INK)
        c.setStrokeColor(MUT)
        c.setLineWidth(0.8)
        c.line(W - 210, 112, W - 90, 112)
        c.line(90, 112, 210, 112)
        c.showPage()
    c.save()
    return buf.getvalue()


def cert_ui(students):
    sec("شهادات التقدير")
    mode = st.radio("نوع الشهادة", ["أوائل الشهر", "إتمام سورة", "وسام الشهر"], horizontal=True, key="cmode")
    items, key = [], ""
    if mode == "أوائل الشهر":
        mo = st.selectbox("الشهر", recent_months(), format_func=month_label, key="cmo")
        n = st.slider("عدد الأوائل", 1, 5, 3, key="cn")
        S, rk, tot = month_bundle(mo)
        top = sorted([x for x in students if x["id"] in rk], key=lambda x: (rk[x["id"]], x["name"]))[:n]
        for x in top:
            r = rk[x["id"]]
            items.append((x["name"], f"تقديرا لحصوله على المرتبة {ORD_AR.get(r, str(r))} في القسم لشهر {month_label(mo)}", "لانضباطه وحضوره ومواظبته على الحفظ والمراجعة، زاده الله توفيقا"))
        key = f"top{mo}{n}"
        st.caption("الأسماء: " + ("، ".join(x["name"] for x in top) if top else "لا توجد بيانات في هذا الشهر."))
    elif mode == "وسام الشهر":
        mo = st.selectbox("الشهر", recent_months(), format_func=month_label, key="cmo2")
        bt = st.selectbox("الوسام", ["حضور كامل", "انضباط ممتاز", "ثلاثة أشهر متتالية في الأوائل", "أتمّ حفظ الحزب"], key="cbt")
        S, rk, tot = month_bundle(mo)
        got = [(x, tx) for x in students for _ic, tx in S.get(x["id"], {}).get("badges", []) if bt in tx]
        for x, tx in got:
            items.append((x["name"], f"تقديرا لنيله وسام «{tx}» في شهر {month_label(mo)}", "بارك الله فيه وزاده حرصا وتوفيقا"))
        key = f"bd{mo}{bt}"
        st.caption("الأسماء: " + ("، ".join(x["name"] for x, _ in got) if got else "لا أحد نال هذا الوسام في هذا الشهر."))
    else:
        if not students:
            st.caption("لا يوجد طلبة.")
            return
        stu = st.selectbox("الطالب", students, format_func=lambda x: x["name"], key="cst")
        memo = memo_of([l for l in load("logs") if l["sid"] == stu["id"] and l["type"] == "hifz"])
        full = sorted((sn for sn, v in memo.items() if len(v) == SURAHS[sn - 1][1]), reverse=True)
        if not full:
            st.caption("لم يُتمّ هذا الطالب سورة كاملة مسجَّلة بعد.")
        pick = st.multiselect("السور المكتملة", full, default=full[:1], format_func=lambda k: SURAHS[k - 1][0], key=f"csu{stu['id']}")
        for k in pick:
            items.append((stu["name"], f"تقديرا لإتمامه حفظ سورة {SURAHS[k - 1][0]}", "نسأل الله أن يبارك فيه ويجعله من أهل القرآن"))
        key = f"sur{stu['id']}{pick}"
    if items and st.button("تجهيز الشهادات (PDF)", key="cb"):
        try:
            st.session_state["cert"] = (key, cert_pdf(items))
            audit("شهادات تقدير", f"{len(items)} شهادة: " + "، ".join(i_[0] for i_ in items[:5]))
        except Exception as e:
            st.error(f"تعذّر إعداد الشهادات: {e}")
    cr = st.session_state.get("cert")
    if cr and cr[0] == key and items:
        st.download_button("تحميل الشهادات (PDF)", cr[1], file_name="شهادات-تقدير.pdf", mime="application/pdf", key="cd", type="primary")


def staff_watch():
    """للمدير: كل ما أدخله المشايخ من حضور وانضباط وحفظ ومراجعة في فترة محددة."""
    sec("متابعة ما يدخله المشايخ")
    today = now().date()
    rng = st.date_input("الفترة", value=(today, today), key="swr")
    rng = list(rng) if isinstance(rng, (tuple, list)) else [rng]
    d1, d2 = rng[0].isoformat(), rng[-1].isoformat()
    students = load("students")
    nm = {x["id"]: x["name"] for x in students}
    att = [a for a in load("att") if d1 <= a["date"] <= d2]
    dsc = [d for d in load("disc") if d1 <= d["date"] <= d2]
    lg = [l for l in load("logs") if d1 <= l["date"] <= d2]
    st.caption(f"من {d1} إلى {d2}")
    summ = []
    for t in STAFF:
        dv = [int(d["score"]) for d in dsc if d["teacher"] == t["n"] and d["score"] in ("1", "2", "3")]
        summ.append({"الشيخ": t["n"], "سجّل حضورا": str(sum(a["teacher"] == t["n"] for a in att)),
                     "سجّل انضباطا": str(len(dv)), "معدل ما قيّمه": f"{sum(dv) / len(dv):.2f}" if dv else "—",
                     "حفظ": str(sum(l["teacher"] == t["n"] and l["type"] == "hifz" for l in lg)),
                     "مراجعة": str(sum(l["teacher"] == t["n"] and l["type"] != "hifz" for l in lg))})
    st.dataframe(summ, width="stretch", hide_index=True)
    for k, t in enumerate(TEACHERS):
        if t.get("admin"):
            continue
        grp = [x for x in students if x["grp"] == str(k)]
        done = {a["sid"] for a in att if a["date"] == d2}
        miss = [x["name"] for x in grp if x["id"] not in done]
        if grp and miss:
            st.markdown(f'<div class="note">{esc(t["n"])}: لم يُسجَّل حضور {len(miss)} من {len(grp)} طالبا يوم {d2}: ' + "، ".join(esc(n) for n in miss[:15]) + "</div>", unsafe_allow_html=True)
        elif grp:
            st.markdown(f'<div class="pay ok">{esc(t["n"])}: سُجّل حضور كل طلبته يوم {d2}.</div>', unsafe_allow_html=True)
    who_ = st.selectbox("عرض تفاصيل", ["الكل"] + [t["n"] for t in STAFF], key="swt")
    ok = lambda r: who_ == "الكل" or r["teacher"] == who_
    with st.expander(f"تفاصيل الحضور ({sum(1 for a in att if ok(a))})"):
        rows = [{"التاريخ": a["date"], "الطالب": nm.get(a["sid"], "—"), "الحضور": ATT.get(a["status"], a["status"]), "الشيخ": a["teacher"] or "—",
                 "ملاحظة": ("بتبرير الولي: " + a.get("why", "")) if a.get("by") == "parent" else ""} for a in sorted(att, key=lambda a: a["date"], reverse=True) if ok(a)]
        st.dataframe(rows[:300], width="stretch", hide_index=True) if rows else st.caption("لا تسجيل.")
    with st.expander(f"تفاصيل الانضباط ({sum(1 for d in dsc if ok(d))})"):
        rows = [{"التاريخ": d["date"], "الطالب": nm.get(d["sid"], "—"), "الانضباط": DISC.get(int(d["score"]), d["score"]) if d["score"] in ("1", "2", "3") else "—", "الشيخ": d["teacher"]}
                for d in sorted(dsc, key=lambda d: d["date"], reverse=True) if ok(d)]
        st.dataframe(rows[:300], width="stretch", hide_index=True) if rows else st.caption("لا تسجيل.")
    with st.expander(f"تفاصيل الحفظ والمراجعة ({sum(1 for l in lg if ok(l))})"):
        rows = [{"التاريخ": l["date"], "الطالب": nm.get(l["sid"], "—"), "النوع": "حفظ" if l["type"] == "hifz" else "مراجعة", "التفاصيل": l["detail"], "التقدير": l["grade"], "الشيخ": l["teacher"]}
                for l in sorted(lg, key=lambda l: l["date"], reverse=True) if ok(l)]
        st.dataframe(rows[:300], width="stretch", hide_index=True) if rows else st.caption("لا تسجيل.")


def admin_tab():
    students = sorted(load("students"), key=lambda s: s["name"])
    staff_watch()
    sec("متابعة وتنبيهات")
    admin_extras(students)
    sec("إضافة طلبة")
    with st.form("add", clear_on_submit=True):
        names = st.text_area("اكتب كل اسم في سطر (يمكن لصق القائمة كاملة)", height=120)
        if st.form_submit_button("إضافة", type="primary"):
            ns = [n.strip() for n in names.splitlines() if n.strip()]
            exist = {s["name"] for s in students}
            ns = [n for n in ns if n not in exist]
            if not ns:
                st.error("لا توجد أسماء جديدة")
            else:
                STORE.add_many("students", [{"name": n, "grp": "1" if SOLO else "", "pin": "", "days": "", "exempt": "", "mdays": ""} for n in ns])
                _load.clear()
                audit("إضافة طلبة", "، ".join(ns)[:200])
                st.success(f"✓ تمت إضافة {len(ns)} طالب")
                st.rerun()

    if not SOLO:
        sec("التوزيع على المشايخ")
        st.caption(f"الحفظ والمراجعة عند {DIR_N} لجميع الطلبة، وتُقسَّم أيام المراجعة بين فوجين." if SOLO else f"الحفظ عند {DIR_N} لجميع الطلبة، والمراجعة تُقسَّم بالتناوب بين {REV1_N} و{REV2_N}.")
        c1, c2 = st.columns(2)
        if c1.button("توزيع حسب السجلات"):
            res = distribute_by_records(students, load("logs"))
            STORE.update_many("students", {sid: {"grp": g} for sid, g in res.items()})
            _load.clear()
            audit("توزيع حسب السجلات", f"{len(res)} طالب")
            st.success("✓ وُزّع الطلبة حسب آخر مراجعة سُجّلت لكل طالب، والباقي بالتساوي")
            st.rerun()
        if c2.button("توزيع بالتناوب"):
            STORE.update_many("students", {s["id"]: {"grp": str(k % 2 + 1)} for k, s in enumerate(students)})
            _load.clear()
            audit("توزيع بالتناوب", f"{len(students)} طالب")
            st.success("✓ تم التوزيع بالتناوب")
            st.rerun()

    sec("أيام المراجعة (فوجان)")
    st.caption("تُقسَّم أيام المراجعة بين فوجين متساويين: الفوج الأول السبت والثلاثاء، والفوج الثاني الأحد والأربعاء، بترتيب الأسماء." if SOLO else "طلبة كل شيخ مراجعة يُقسَّمون إلى فوجين متساويين: الفوج الأول السبت والثلاثاء، والفوج الثاني الأحد والأربعاء. يُقسَّم طلبة كل شيخ على حدة بترتيب الأسماء.")
    c1, c2 = st.columns(2)
    for col, lab, only_new in ((c1, "تقسيم من لم تُعيَّن أيامهم", True), (c2, "إعادة تقسيم الجميع", False)):
        if col.button(lab, key=f"split{int(only_new)}"):
            ch, skipped = {}, 0
            for g in REV_SHEIKH:
                grp_ = [x for x in students if x["grp"] == g]
                for k, x in enumerate(grp_):
                    if only_new and mdays_of(x):
                        continue
                    ch[x["id"]] = {"mdays": MFOJ["A" if k % 2 == 0 else "B"]}
            skipped = sum(1 for x in students if x["grp"] not in REV_SHEIKH)
            if ch:
                STORE.update_many("students", ch)
                _load.clear()
                audit("تقسيم المراجعة إلى فوجين", f"{len(ch)} طالب")
            st.session_state["split_msg"] = f"✓ عُيّنت أيام المراجعة لـ {len(ch)} طالب" + (f". لم يُوجَّه بعد إلى شيخ مراجعة: {skipped} طالب، وجّههم أولا." if skipped else "")
            st.rerun()
    if st.session_state.get("split_msg"):
        st.success(st.session_state["split_msg"])

    sec("الجدول العام للطلبة")
    full = sorted(students, key=lambda x: (x["grp"] or "9", x["name"]))
    st.dataframe(
        [{"الطالب": x["name"], f"أيام الحفظ ({short_n(DIR_N)})": names_of(days_of(x), DAYS) or "—",
          "شيخ المراجعة": REV_SHEIKH.get(x["grp"], "لم يُوجَّه"), "أيام المراجعة": names_of(mdays_of(x), MDAYS) or "—"} for x in full],
        width="stretch", hide_index=True,
    )
    day_rows = []
    for code, (lab, _) in MDAYS.items():
        day_rows.append({"اليوم": lab,
                         f"حفظ ({short_n(DIR_N)})": sum(code in days_of(x) for x in students),
                         f"مراجعة ({short_n(REV1_N)})": sum(code in mdays_of(x) and x["grp"] == "1" for x in students),
                         **({} if SOLO else {f"مراجعة ({short_n(REV2_N)})": sum(code in mdays_of(x) and x["grp"] == "2" for x in students)})})
    st.caption("عدد الطلبة في كل يوم:")
    st.dataframe(day_rows, width="stretch", hide_index=True)

    if SEEDED:
        sec("أيام الحفظ")
        st.caption("الأحد: 13 طالبا، والأربعاء: 11 طالبا (حسيد أنيس في اليومين). يوم الثلاثاء تختاره أنت لكل طالب من بطاقته. تُطابَق الأسماء تلقائيا مع قائمة الطلبة.")
        if st.button("تعيين أيام الحفظ من القائمة"):
            days, miss = {}, []
            for key, names in (("sun", SUN_NAMES), ("wed", WED_NAMES)):
                for n in names:
                    m = match_student(n, students)
                    if m:
                        days.setdefault(m["id"], []).append(key)
                    else:
                        miss.append(n)
            STORE.update_many("students", {sid: {"days": ",".join(v)} for sid, v in days.items()})
            _load.clear()
            audit("تعيين أيام الحفظ", f"{len(days)} طالب")
            st.session_state["days_miss"] = miss
            st.session_state["days_n"] = len(days)
            st.rerun()
        if "days_n" in st.session_state:
            st.success(f"✓ عُيّنت أيام الحفظ لـ {st.session_state['days_n']} طالب")
            if st.session_state.get("days_miss"):
                st.warning("لم يُعثر في القائمة على: " + "، ".join(st.session_state["days_miss"]) + ". عيّن أيامهم يدويا من بطاقة الطالب.")

    sec("أيام بلا حلقة (عطل وأعياد)")
    st.caption("لا دراسة الاثنين والخميس والجمعة، وتُستثنى تلقائيا. سجّل هنا أي يوم آخر بلا حلقة (عيد، عطلة…) فلا يُحتسب ضمن حصص الشهر.")
    hd_ = st.date_input("تاريخ العطلة", value=now().date(), key="hold").isoformat()
    h1, h2 = st.columns(2)
    if h1.button("تسجيل كعطلة", key="holb"):
        cfg_set("holidays", ",".join(sorted(holidays() | {hd_})))
        audit("عطلة", hd_)
        st.rerun()
    _cur = sorted(holidays())
    if _cur:
        _rm = st.multiselect("العطل المسجَّلة", _cur, key="holrm")
        if _rm and h2.button("إلغاء المحدد", key="holc"):
            cfg_set("holidays", ",".join(d_ for d_ in _cur if d_ not in _rm))
            audit("إلغاء عطلة", ",".join(_rm))
            st.rerun()

    sec("التقارير الشهرية وترتيب الحلقة")
    mo = st.selectbox("الشهر", recent_months(), format_func=month_label, key="admo")
    S, rk, tot = month_bundle(mo)
    rows = sorted([s for s in students if s["id"] in rk], key=lambda s: (rk[s["id"]], s["name"]))
    if rows:
        st.dataframe(
            [{"الترتيب": rk[s["id"]], "الطالب": s["name"], "النقاط": f'{S[s["id"]]["score"]:g}',
              "الانضباط": f'{S[s["id"]]["dis"]:.2f}' if S[s["id"]]["dis"] is not None else "—",
              "الحضور %": f'{S[s["id"]]["pct"]:g}' if S[s["id"]]["pct"] is not None else "—",
              "المراجعة": grade_name(S[s["id"]]["mur"]), "آيات الشهر": S[s["id"]]["aya"], "حصص الحفظ": len(S[s["id"]]["hl"])}
             for s in rows],
            width="stretch", hide_index=True,
        )
    else:
        st.caption("لا توجد بيانات في هذا الشهر.")
    st.caption(f"الفترة: {month_range_label(mo)}")
    st.caption("نقاط الترتيب من 100: " + " + ".join(f"{HW_NAMES[k]} {HW[k]}" for k in HW) + ".")
    ht = st.number_input("هدف الحفظ الشهري (عدد الآيات للحصول على كامل نقاط التقدم)", min_value=1, max_value=600, value=hifz_target(), step=5, key="htg")
    st.caption("يمكنك تحديد هدف خاص لكل طالب من بطاقته في تبويب «التسجيل»، وهو يتقدم على هذا الهدف العام.")
    _er = st.checkbox("اعتماد الاختبارات في الترتيب (تعطي 10% من المجموع لمن اختُبر في الشهر)", value=cfg_get("exam_rank") == "1", key="examrk")
    if _er != (cfg_get("exam_rank") == "1"):
        cfg_set("exam_rank", "1" if _er else "0")
        audit("اعتماد الاختبارات في الترتيب", "تفعيل" if _er else "إيقاف")
        st.rerun()
    if ht != hifz_target() and st.button("حفظ الهدف", key="htb"):
        cfg_set("hifz_target", ht)
        audit("هدف الحفظ الشهري", str(ht))
        st.rerun()
    if st.button("تجهيز تقرير القسم (PDF من صفحة واحدة)", key="deptb"):
        try:
            with st.spinner("جارٍ إعداد التقرير…"):
                st.session_state["dept_rep"] = (mo, dept_pdf(mo))
        except Exception as e:
            st.error(f"تعذّر إعداد التقرير: {e}")
    dr = st.session_state.get("dept_rep")
    if dr and dr[0] == mo:
        st.download_button("تحميل تقرير القسم (PDF)", dr[1], file_name=f"تقرير-القسم-{mo}.pdf", mime="application/pdf", key="deptd", type="primary")
    if students and st.button("تجهيز تقارير جميع الطلبة (ملف ZIP)", key="zipb"):
        try:
            with st.spinner("جارٍ إعداد التقارير…"):
                bundle = month_bundle(mo)
                zb = io.BytesIO()
                with zipfile.ZipFile(zb, "w", zipfile.ZIP_DEFLATED) as z:
                    for s in students:
                        z.writestr(f"{s['name']}-{mo}.pdf", student_pdf(s, mo, bundle))
                st.session_state["zip_rep"] = (mo, zb.getvalue())
        except Exception as e:
            st.error(f"تعذّر إعداد التقارير: {e}")
    zr = st.session_state.get("zip_rep")
    if zr and zr[0] == mo:
        st.download_button("تحميل كل التقارير (ZIP)", zr[1], file_name=f"تقارير-{mo}.zip", mime="application/zip", key="zipd", type="primary")

    sec("رموز الأولياء")
    if st.button("توليد رموز الأولياء"):
        used = {s["pin"] for s in students if s["pin"]}
        ch = {}
        for s in students:
            if s["pin"]:
                continue
            while True:
                p = f"{random.SystemRandom().randrange(10**6):06d}"
                if p not in used:
                    break
            used.add(p)
            ch[s["id"]] = {"pin": p}
        n = len(ch)
        if ch:
            STORE.update_many("students", ch)
            audit("توليد رموز الأولياء", f"{n} رمز")
        _load.clear()
        st.success(f"✓ تم توليد {n} رمز. أرسل كل رمز لوليّ الطالب وحده من بطاقة الطالب، ولا تنشر القائمة في المجموعة.")
        st.rerun()
    if students:
        st.dataframe(
            [{"الطالب": s["name"], "المجموعة": s["grp"] or "—", "الاشتراك": "معفى" if s.get("exempt") == "1" else "—", "أيام الحفظ": "، ".join(DAYS[k][0] for k in days_of(s)) or "—", "أيام المراجعة": "، ".join(MDAYS[k][0] for k in mdays_of(s)) or "—", "رمز الولي": s["pin"] or "—"} for s in students],
            width="stretch", hide_index=True,
        )

    cert_ui(students)

    sec("نسخة احتياطية")
    st.caption("حمّل نسخة من كل البيانات (ملف ZIP فيه جدول لكل ورقة) واحفظها عندك، مرة في الأسبوع مثلا. تُفتح الملفات بـ Excel.")
    if st.button("تجهيز النسخة الاحتياطية", key="bkb"):
        try:
            zb = io.BytesIO()
            with zipfile.ZipFile(zb, "w", zipfile.ZIP_DEFLATED) as z:
                for n_, cols in HEAD.items():
                    sio = io.StringIO()
                    w_ = csv.writer(sio)
                    w_.writerow(cols)
                    for r_ in load(n_):
                        w_.writerow([r_.get(k, "") for k in cols])
                    z.writestr(f"{n_}.csv", "\ufeff" + sio.getvalue())
            st.session_state["bk"] = (now().strftime("%Y-%m-%d"), zb.getvalue())
            audit("نسخة احتياطية", "تحميل")
        except Exception as e:
            st.error(f"تعذّر إعداد النسخة: {explain(e)}")
    bk = st.session_state.get("bk")
    if bk:
        st.download_button("تحميل النسخة الاحتياطية (ZIP)", bk[1], file_name=f"نسخة-الفرقان-{bk[0]}.zip", mime="application/zip", key="bkd", type="primary")

    sec("حذف طالب")
    if students:
        d = st.selectbox("الطالب", students, format_func=lambda x: x["name"], key="delsel")
        sure = st.checkbox("أؤكد حذف الطالب وكل تسجيلاته نهائياً")
        if st.button("حذف الطالب", disabled=not sure):
            for n in ("logs", "att", "pay", "disc", "msg", "visits"):
                STORE.delete_by_sid(n, d["id"])
            STORE.delete("students", d["id"])
            _load.clear()
            audit("حذف طالب", d["name"])
            st.success("✓ تم الحذف")
            st.rerun()


# ───────────────────────── دردشة المشايخ ─────────────────────────
EMOJIS = ["👍", "🤲", "🌹", "😊", "🙏", "✅", "❌", "⚠️", "📖", "⭐", "❤️", "🕌", "⏰", "📞", "🤝", "😂"]


def _seen_key(i):
    return f"chatseen_{TEACHERS[i]['u']}"


def chat_for(i):
    me = TEACHERS[i]["u"]
    return sorted([m for m in load("chat") if m["to"] == "all" or m["to"] == me or m["who"] == me], key=lambda m: (m["ts"], m["id"]))


def chat_unread(i):
    me = TEACHERS[i]["u"]
    seen = cfg_get(_seen_key(i), "")
    new = [m for m in chat_for(i) if m["who"] != me and m["ts"] > seen]
    return len(new), sum(1 for m in new if m["kind"] == "alert")


def _chat_send(i, tkey, okey, akey):
    me = TEACHERS[i]
    txt = (st.session_state.get(tkey) or "").strip()[:1000]
    if not txt:
        st.session_state["chat_flash"] = ("err", "اكتب رسالة أولا")
        return
    to = st.session_state.get(okey, "all")
    try:
        write(STORE.add, "chat", {"ts": stamp(), "who": me["u"], "to": to, "text": txt, "kind": "alert" if st.session_state.get(akey) else ""})
        cfg_set(_seen_key(i), stamp())
    except Exception as e:
        st.session_state["chat_flash"] = ("err", f"تعذّر الإرسال: {explain(e)}")
        return
    st.session_state[tkey] = ""
    st.session_state[akey] = False
    st.session_state["chat_flash"] = ("ok", "✓ أُرسلت الرسالة")


def _chat_emoji(tkey, pkey):
    e = st.session_state.get(pkey)
    if e:
        st.session_state[tkey] = (st.session_state.get(tkey) or "") + e
        st.session_state[pkey] = None


def chat_tab(i):
    me = TEACHERS[i]
    sec("دردشة المشايخ")
    st.caption("محادثة خاصة بالمشايخ فقط: مع الجميع أو مع شيخ بعينه، ويمكن إرسال تنبيه عاجل 🔔.")
    fl = st.session_state.pop("chat_flash", None)
    if fl:
        (st.success if fl[0] == "ok" else st.error)(fl[1])
    others = [t for t in TEACHERS if t["u"] != me["u"]]
    opts = ["all"] + [t["u"] for t in others]
    with_ = st.radio("المحادثة", opts, horizontal=True, key=f"cw{i}", format_func=lambda u: "الجميع" if u == "all" else TKEY[u]["n"])
    allm = chat_for(i)
    if with_ == "all":
        thread = [m for m in allm if m["to"] == "all"]
    else:
        thread = [m for m in allm if m["to"] != "all" and {m["who"], m["to"]} == {me["u"], with_}]
    seen = cfg_get(_seen_key(i), "")
    out = []
    for m in thread[-60:]:
        mine_ = m["who"] == me["u"]
        new = (not mine_) and m["ts"] > seen
        alert = m["kind"] == "alert"
        nm_ = TKEY[m["who"]]["n"] if m["who"] in TKEY else m["who"]
        out.append(f'<div class="bub{" me" if mine_ else ""}{" new" if new else ""}"' + (' style="border-color:#b3261e;background:#fdf1ee"' if alert else "") +
                   f'><div class="mt">{"🔔 تنبيه · " if alert else ""}{esc(nm_)} · {esc(m["ts"][:16])}{" · جديد" if new else ""}</div>{esc(m["text"]).replace(chr(10), "<br>")}</div>')
    st.markdown("".join(out) or '<div class="empty">لا رسائل بعد. ابدأ المحادثة 👋</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    if c1.button("تحديث", key=f"cr{i}"):
        _load.clear()
        st.rerun()
    if c2.button("تم الاطلاع على الكل", key=f"cs{i}"):
        cfg_set(_seen_key(i), stamp())
        st.rerun()
    tkey, pkey, akey, okey = f"ct{i}", f"cp{i}", f"ca{i}", f"co{i}"
    st.session_state[okey] = with_
    st.text_area("رسالتك", key=tkey, height=90, max_chars=1000, placeholder="اكتب هنا… ويمكنك إضافة الإيموجي من الأسفل")
    if hasattr(st, "pills"):
        st.pills("إضافة رمز", EMOJIS, selection_mode="single", key=pkey, on_change=_chat_emoji, args=(tkey, pkey), label_visibility="collapsed")
    st.checkbox("🔔 أرسلها كتنبيه عاجل", key=akey)
    st.button("إرسال", type="primary", key=f"cb{i}", on_click=_chat_send, args=(i, tkey, okey, akey))


# ───────────────────────── ملخص الحلقة (للمدير) ─────────────────────────
def short_log(l):
    if l.get("kind") == "none" or l.get("grade") == "لم يحفظ":
        return "لم يحفظ"
    sn = int(l["sur"]) if str(l.get("sur", "")).isdigit() else 0
    if aya_set(l):
        a1, a2 = int(l["a1"]), int(l["a2"])
        s2 = int(l["sur2"]) if str(l.get("sur2", "")).isdigit() and l.get("sur2") != l.get("sur") else 0
        if s2:
            t = f"{SURAHS[sn - 1][0]} {a1} ← {SURAHS[s2 - 1][0]} {a2}"
        else:
            t = f"{SURAHS[sn - 1][0]} {a1}" + (f"–{a2}" if a2 != a1 else "")
    else:
        t = (l.get("detail") or "")[:30]
    tag = KIND_TAG.get(l.get("kind", ""))
    return (f"[{tag}] " if tag else "") + t + (f" ({l['grade']})" if l.get("grade") else "")


def day_data(day):
    students = sorted(load("students"), key=lambda x: x["name"])
    att = {a["sid"]: a for a in load("att") if a["date"] == day}
    dsc = {}
    for d_ in load("disc"):
        if d_["date"] == day and d_["score"] in ("1", "2", "3"):
            dsc.setdefault(d_["sid"], []).append(int(d_["score"]))
    lg = {}
    for l in load("logs"):
        if l["date"] == day:
            lg.setdefault(l["sid"], []).append(l)
    S, rk, tot = month_bundle(day[:7])
    rows = []
    for x in students:
        sid = x["id"]
        a = att.get(sid)
        dv = dsc.get(sid, [])
        dis = round(sum(dv) / len(dv), 2) if dv else None
        hl = [l for l in lg.get(sid, []) if l["type"] == "hifz"]
        ml = [l for l in lg.get(sid, []) if l["type"] != "hifz"]
        gp = lambda ls: (sum(GPTS.get(l["grade"], 0) for l in ls) / len(ls)) if ls else 0
        aya = len(set().union(*[aya_set(l) for l in hl])) if hl else 0
        rows.append({
            "id": sid, "name": x["name"], "att": a["status"] if a else None, "dis": dis,
            "hifz": " + ".join(short_log(l) for l in hl) or "—",
            "mur": " + ".join(short_log(l) + " · " + l["teacher"].replace("الشيخ ", "") for l in ml) or "—",
            "rank": rk.get(sid), "score": S[sid]["score"] if sid in rk else None,
            "key": (dis or 0, 1 if a and a["status"] == "p" else 0, gp(ml), gp(hl), aya),
            "any": bool(a or dv or lg.get(sid)),
        })
    rows.sort(key=lambda r: (r["rank"] is None, r["rank"] or 0, r["name"]))
    cnt = {k: sum(1 for r in rows if r["att"] == k) for k in ("p", "l", "a", "e")}
    cnt["none"] = sum(1 for r in rows if r["att"] is None)
    dvs = [r["dis"] for r in rows if r["dis"] is not None]
    stars = [r["name"] for r in sorted([r for r in rows if r["att"] in ("p", "l") and r["any"]], key=lambda r: r["key"], reverse=True)[:3] if r["key"][0] or r["key"][2] or r["key"][3]]
    return rows, cnt, (round(sum(dvs) / len(dvs), 2) if dvs else None), stars


def day_pdf(day, rows, cnt, davg, stars):
    from reportlab.lib.colors import HexColor, white
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfgen import canvas

    if not os.path.exists(FONT):
        raise RuntimeError("ملف الخط Amiri-Regular.ttf غير موجود في GitHub بجانب app.py")
    if "Amiri" not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont("Amiri", FONT))
    INK, GOLD, PAPER, LINE, MUT = HexColor("#0a4a3e"), HexColor("#a9822a"), HexColor("#f3f5ee"), HexColor("#d6ddcb"), HexColor("#5f6f67")
    W, H = landscape(A4)
    L, R = 30, W - 30
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(W, H))
    c.setTitle(f"ملخص الحلقة {day}")

    def put(x, y, t, size=12, align="r", color=INK, maxw=None):
        t = _shape(str(t))
        if maxw:
            while c.stringWidth(t, "Amiri", size) > maxw and size > 7:
                size -= 0.5
        c.setFont("Amiri", size)
        c.setFillColor(color)
        {"r": c.drawRightString, "l": c.drawString, "c": c.drawCentredString}[align](x, y, t)

    c.setFillColor(INK)
    c.rect(0, H - 62, W, 62, stroke=0, fill=1)
    c.setFillColor(GOLD)
    c.rect(0, H - 65, W, 3, stroke=0, fill=1)
    lp = os.path.join(HERE, "logo.jpg")
    if os.path.exists(lp):
        c.setFillColor(white)
        c.roundRect(L, H - 56, 48, 48, 8, stroke=0, fill=1)
        c.drawImage(lp, L + 3, H - 53, 42, 42, preserveAspectRatio=True, mask="auto")
    put(R, H - 30, f"{ASSOC} – {SEC}", 20, "r", white)
    d_ = dt.date.fromisoformat(day)
    put(R, H - 52, f"ملخص الحلقة  ·  {WEEKDAYS_AR[d_.weekday()]} {d_.day} {MONTHS_AR[d_.month - 1]} {d_.year}", 13, "r", HexColor("#e8d9a0"))
    y = H - 88
    put(R, y, f"حاضر {cnt['p'] + cnt['l']}" + (f" (منهم {cnt['l']} متأخر)" if cnt["l"] else "") + f"   ·   غائب {cnt['a']}   ·   غياب بعذر {cnt['e']}   ·   لم يُسجَّل {cnt['none']}   ·   معدل الانضباط: " + (f"{davg:.2f} من 3" if davg is not None else "—"), 12.5, "r", INK)
    if stars:
        y -= 20
        put(R, y, "نجوم الحلقة: " + "، ".join(stars), 13, "r", GOLD)
    cols = [("الترتيب", 44), ("الطالب", 0), ("الحضور", 56), ("الانضباط", 62), ("الحفظ", 170), ("المراجعة", 190), ("نقاط الشهر", 56)]
    widths = [w or (R - L - sum(w2 for _, w2 in cols)) for _, w in cols]
    y -= 14
    avail = y - 50
    rh = max(11.5, min(19.0, (avail - 19) / max(len(rows), 1)))
    y -= 19
    c.setFillColor(INK)
    c.rect(L, y, R - L, 19, stroke=0, fill=1)
    x = R
    for (h_, _), w in zip(cols, widths):
        put(x - 6, y + 5, h_, 10.5, "r", white)
        x -= w
    fs = 11 if rh >= 16 else 9.5
    for k, r in enumerate(rows):
        y -= rh
        if k % 2 == 0:
            c.setFillColor(PAPER)
            c.rect(L, y, R - L, rh, stroke=0, fill=1)
        vals = [str(r["rank"]) if r["rank"] else "—", r["name"], ATT.get(r["att"], "—") if r["att"] else "—",
                disc_label(r["dis"]) if r["dis"] is not None else "—", r["hifz"], r["mur"], f"{r['score']:g}" if r["score"] is not None else "—"]
        x = R
        for t, w in zip(vals, widths):
            put(x - 6, y + (rh - fs) / 2 + 1.5, t, fs, "r", INK, maxw=w - 10)
            x -= w
    c.setStrokeColor(LINE)
    c.line(L, 44, R, 44)
    put(W / 2, 28, "الترتيب بنقاط الشهر حتى هذا اليوم: انضباط 25 + حضور 25 + مراجعة 20 + تقدم الحفظ 15 + تقدير الحفظ 15", 9.5, "c", MUT)
    c.showPage()
    c.save()
    return buf.getvalue()


def summary_tab():
    sec("ملخص الحلقة")
    st.caption(f"كل ما سُجّل في الحلقة من حفظ ومراجعة ({DIR_N}) وحضور وانضباط، مع ترتيب الشهر، لتلقي نتائجها على الطلبة." if SOLO else f"كل ما سُجّل في الحلقة من حفظ ({DIR_N}) ومراجعة (الشيخان) وحضور وانضباط، مع ترتيب الشهر، لتلقي نتائجها على الطلبة.")
    day = st.date_input("يوم الحلقة", value=now().date(), key="sumd").isoformat()
    rows, cnt, davg, stars = day_data(day)
    if not rows:
        st.info("لا يوجد طلبة بعد.")
        return
    if not any(r["any"] for r in rows):
        st.markdown('<div class="empty">لا يوجد أي تسجيل في هذا اليوم.</div>', unsafe_allow_html=True)
        return
    st.markdown(
        f'<div class="pay ok">حاضر {cnt["p"] + cnt["l"]}' + (f' (منهم {cnt["l"]} متأخر)' if cnt["l"] else "") + f' · غائب {cnt["a"]} · غياب بعذر {cnt["e"]} · لم يُسجَّل {cnt["none"]}'
        + (f" · معدل الانضباط {davg:.2f} من 3" if davg is not None else "") + "</div>", unsafe_allow_html=True)
    if stars:
        st.markdown('<div class="note">⭐ نجوم الحلقة: ' + "، ".join(esc(n) for n in stars) + "</div>", unsafe_allow_html=True)
    lg = [l for l in load("logs") if l["date"] == day]
    att = [a for a in load("att") if a["date"] == day]
    dsc = [d for d in load("disc") if d["date"] == day]
    lines = []
    for t in STAFF:
        lines.append({"الشيخ": t["n"], "حضور": str(sum(a["teacher"] == t["n"] for a in att)), "انضباط": str(sum(d["teacher"] == t["n"] for d in dsc)),
                      "حفظ": str(sum(l["teacher"] == t["n"] and l["type"] == "hifz" for l in lg)), "مراجعة": str(sum(l["teacher"] == t["n"] and l["type"] != "hifz" for l in lg))})
    st.dataframe(lines, width="stretch", hide_index=True)
    st.dataframe([{"الترتيب": str(r["rank"]) if r["rank"] else "—", "الطالب": r["name"], "الحضور": ATT.get(r["att"], "—") if r["att"] else "—",
                   "الانضباط": disc_label(r["dis"]) if r["dis"] is not None else "—", "الحفظ": r["hifz"], "المراجعة": r["mur"],
                   "نقاط الشهر": f"{r['score']:g}" if r["score"] is not None else "—"} for r in rows], width="stretch", hide_index=True)
    d_ = dt.date.fromisoformat(day)
    top = [r for r in rows if r["rank"]][:5]
    txt = [f"نتائج حلقة {WEEKDAYS_AR[d_.weekday()]} {d_.day} {MONTHS_AR[d_.month - 1]} {d_.year}",
           f"الحضور: {cnt['p'] + cnt['l']} حاضر، {cnt['a']} غائب" + (f"، {cnt['e']} بعذر" if cnt["e"] else "")]
    if stars:
        txt.append("⭐ نجوم الحلقة: " + "، ".join(stars))
    if top:
        txt.append("ترتيب الشهر حتى اليوم:")
        txt += [f"{r['rank']}. {r['name']} ({r['score']:g} نقطة)" for r in top]
    txt.append("بارك الله فيكم وزادكم حرصا على القرآن.")
    with st.expander("نص جاهز للنسخ أو الإرسال"):
        st.code("\n".join(txt), language=None)
        st.link_button("إرسال عبر واتساب", wa_link("\n".join(txt)))
    if st.button("تجهيز ملخص الحلقة (PDF)", key="sumb"):
        try:
            st.session_state["sumpdf"] = (day, day_pdf(day, rows, cnt, davg, stars))
        except Exception as e:
            st.error(f"تعذّر إعداد الملخص: {e}")
    sp = st.session_state.get("sumpdf")
    if sp and sp[0] == day:
        st.download_button("تحميل ملخص الحلقة (PDF)", sp[1], file_name=f"ملخص-الحلقة-{day}.pdf", mime="application/pdf", key="sumd2", type="primary")


# ───────────────────────── مؤقت الحلقة ─────────────────────────
ALGIERS = (float(_SC.get("lat", 36.7133)), float(_SC.get("lon", 3.2150)))  # الدار البيضاء، الجزائر العاصمة (يمكن تغييرها من [section])


def _prayer_calc(d):
    """حساب تقريبي بلا إنترنت: الغروب (−0.833°) والعشاء (−17° وفق وزارة الشؤون الدينية الجزائرية)."""
    import math
    lat, lon = ALGIERS
    doy = d.timetuple().tm_yday
    g = 2 * math.pi / 365 * (doy - 1 + 0.0)
    eq = 229.18 * (0.000075 + 0.001868 * math.cos(g) - 0.032077 * math.sin(g) - 0.014615 * math.cos(2 * g) - 0.040849 * math.sin(2 * g))
    dec = (0.006918 - 0.399912 * math.cos(g) + 0.070257 * math.sin(g) - 0.006758 * math.cos(2 * g)
           + 0.000907 * math.sin(2 * g) - 0.002697 * math.cos(3 * g) + 0.00148 * math.sin(3 * g))
    noon = 720 - 4 * lon - eq + 60  # دقائق من منتصف الليل (التوقيت UTC+1)

    def at(angle):
        ch = (math.sin(math.radians(angle)) - math.sin(math.radians(lat)) * math.sin(dec)) / (math.cos(math.radians(lat)) * math.cos(dec))
        return noon + 4 * math.degrees(math.acos(max(-1, min(1, ch))))

    f = lambda m: f"{int(m // 60):02d}:{int(round(m % 60)) % 60:02d}" if round(m % 60) < 60 else f"{int(m // 60) + 1:02d}:00"
    return f(at(-0.833) + 1), f(at(-17))


@st.cache_data(ttl=3600, show_spinner=False)
def _prayer_api(day_iso, ll=None):
    try:
        import json
        import urllib.request
        d = dt.date.fromisoformat(day_iso)
        url = (f"https://api.aladhan.com/v1/timings/{d.day:02d}-{d.month:02d}-{d.year}"
               f"?latitude={(ll or ALGIERS)[0]}&longitude={(ll or ALGIERS)[1]}&method=19&timezonestring=Africa/Algiers")
        with urllib.request.urlopen(url, timeout=4) as r:
            t = json.load(r)["data"]["timings"]
        return t["Maghrib"][:5], t["Isha"][:5]
    except Exception:
        return None


def prayer_times(day_iso):
    """(المغرب، العشاء، المصدر): يدوي من الإدارة، ثم من الإنترنت، ثم تقديري."""
    man = cfg_get(f"pt_{day_iso}", "")
    if re.fullmatch(r"\d\d:\d\d,\d\d:\d\d", man or ""):
        a, b = man.split(",")
        return a, b, "ضُبطت يدويا"
    api = _prayer_api(day_iso, ALGIERS)
    if api:
        return api[0], api[1], "من الإنترنت (الجزائر العاصمة)"
    a, b = _prayer_calc(dt.date.fromisoformat(day_iso))
    return a, b, "تقديرية — اضبطها يدويا من «حلقة اليوم» إن اختلفت"


def halaqa_window(day=None):
    d = day or now().date()
    mg, ish, src = prayer_times(d.isoformat())
    mk = lambda hm: dt.datetime.combine(d, dt.time(int(hm[:2]), int(hm[3:5])), tzinfo=TZ)
    return mk(mg) + dt.timedelta(minutes=5), mk(ish), mg, ish, src


def timer_bar():
    import streamlit.components.v1 as components
    start, end, mg, ish, src = halaqa_window()
    S_, E_ = int(start.timestamp() * 1000), int(end.timestamp() * 1000)
    html = f"""<div dir="rtl" style="font-family:'Reem Kufi','Amiri',sans-serif;background:#0a4a3e;color:#f3e7b8;border-radius:12px;padding:10px 14px;display:flex;justify-content:space-between;align-items:center;gap:10px">
<div><div id="t" style="font-size:.82rem;opacity:.9">…</div><div id="c" style="font-size:1.8rem;font-weight:700;letter-spacing:1px;color:#fff;direction:ltr;text-align:right">--:--:--</div></div>
<div style="font-size:.74rem;text-align:left;line-height:1.7;opacity:.9">بداية الحلقة {start:%H:%M}<br>أذان العشاء {ish}</div></div>
<div style="height:5px;background:#12614f;border-radius:3px;margin-top:6px"><i id="b" style="display:block;height:5px;background:#d4af37;border-radius:3px;width:0"></i></div>
<script>
const S={S_},E={E_};
const p=n=>String(n).padStart(2,'0');
const f=ms=>{{const t=Math.max(0,Math.floor(ms/1000));return p(Math.floor(t/3600))+':'+p(Math.floor(t%3600/60))+':'+p(t%60)}};
function tick(){{
 const n=Date.now(),t=document.getElementById('t'),c=document.getElementById('c'),b=document.getElementById('b');
 if(n<S){{t.textContent='تبدأ الحلقة بعد';c.textContent=f(S-n);b.style.width='0'}}
 else if(n<E){{const left=E-n;t.textContent='الوقت المتبقي للحلقة';c.textContent=f(left);b.style.width=(100*(n-S)/(E-S))+'%';
   c.style.color=left<600000?'#ffb4a2':'#fff'}}
 else{{t.textContent='انتهت الحلقة';c.textContent='00:00:00';b.style.width='100%'}}
}}
tick();setInterval(tick,1000);
</script>"""
    if hasattr(st, "iframe"):
        st.iframe(html, height=104)
    else:
        components.html(html, height=104)
    st.caption(f"تبدأ الحلقة بعد المغرب ({mg}) بخمس دقائق وتنتهي بأذان العشاء — {src}.")


def halaqa_left_note(vis_count_left):
    start, end, *_ = halaqa_window()
    n = now()
    if start <= n < end and vis_count_left:
        mins = (end - n).total_seconds() / 60
        st.caption(f"⏱ بقي {int(mins)} دقيقة، وبقي {vis_count_left} طالبا دون تسجيل حضور: نحو {mins / vis_count_left:.1f} دقيقة لكل طالب.")


def staff_view(i):
    if SOLO:
        header()
        _r = st.radio("أنت تسجّل الآن", [0, 1], format_func=lambda k: "الحفظ" if k == 0 else "المراجعة", horizontal=True, key="solo_role")
        i = _r if _r in (0, 1) else 0
    me = TEACHERS[i]
    if not SOLO:
        header()
    st.markdown(f'<div class="hi">مرحباً {me["n"]}<span class="chip">{me["r"]}</span></div>', unsafe_allow_html=True)
    nun = unread_count(i)
    if nun:
        st.markdown(f'<div class="note">لديك {nun} رسالة جديدة من الأولياء. افتح تبويب «الرسائل».</div>', unsafe_allow_html=True)
    try:
        timer_bar()
    except Exception:
        pass
    if me.get("admin"):
        _np = sum(1 for x in load("students") if x.get("pstatus") == "pending")
        if _np:
            st.markdown(f'<div class="note">🎯 لديك {_np} اقتراح هدف حفظ من الأولياء بانتظار قرارك. افتح «حلقة اليوم».</div>', unsafe_allow_html=True)
    pre_banner(me, i)
    cn, ca = chat_unread(i)
    if cn:
        st.markdown(f'<div class="note">{"🔔 " if ca else ""}لديك {cn} رسالة جديدة من المشايخ' + (f" (منها {ca} تنبيه عاجل)" if ca else "") + '. افتح تبويب «المشايخ».</div>', unsafe_allow_html=True)
    names = ["حلقة اليوم", "التقرير", "التسجيل", "الحضور", "الانضباط", "الرسائل"] + ([] if SOLO else [f"المشايخ ({cn})" if cn else "المشايخ"]) + ["اقتراحات"] + (["ملخص الحلقة", "الإدارة"] if me.get("admin") else [])
    flash_show()
    fns = [lambda: halaqa_tab(i), lambda: report_tab(i), lambda: student_tab(i), lambda: att_tab(i), lambda: disc_tab(i), lambda: msgs_tab(i)] + ([] if SOLO else [lambda: chat_tab(i)]) + [lambda: sug_tab(i)]
    if me.get("admin"):
        fns += [summary_tab, admin_tab]
    idx = list(range(len(names)))
    if os.environ.get("FURQAN_ALL_TABS") == "1":  # للاختبارات: يُحسب كل قسم كما في التبويبات القديمة
        tabs = st.tabs(names)
        for k in idx:
            with tabs[k]:
                fns[k]()
    else:
        # الحساب للقسم المفتوح وحده: أسرع بكثير من بناء كل التبويبات في كل نقرة
        try:
            st.segmented_control("القسم", idx, default=0, format_func=lambda k: names[k], key="staff_tab", label_visibility="collapsed")
        except AttributeError:
            st.radio("القسم", idx, format_func=lambda k: names[k], key="staff_tab", horizontal=True, label_visibility="collapsed")
        cur = st.session_state.get("staff_tab")
        cur = cur if cur in idx else 0
        fns[cur]()
    st.markdown('<div class="foot"></div>', unsafe_allow_html=True)
    if st.button("تسجيل الخروج"):
        st.session_state.me = None
        st.session_state.pop("staff_tab", None)
        st.session_state.pop("sec_key", None)
        st.session_state.pop("solo_role", None)
        st.rerun()


# ───────────────────────── التشغيل ─────────────────────────
def parent_picker():
    header("متابعة الطالب", basmala=True)
    sec("اختر القسم")
    st.markdown('<div class="lead">اختر قسم ابنكم، ثم أدخلوا الرمز السري الذي أرسلته إليكم الإدارة.</div>', unsafe_allow_html=True)
    for k, c in SECS.items():
        if st.button(c.get("name", k), key=f"pk_{k}"):
            st.query_params["s"] = k
            st.rerun()


if st.query_params.get("v") == "p":
    parent_picker() if GENERIC else parent_view()
elif st.session_state.get("me") is not None and not GENERIC:
    staff_view(st.session_state.me)
else:
    login_view()
