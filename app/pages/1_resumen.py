"""Página 1 · Resumen: KPIs, hallazgo principal y fecha de actualización."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st  # noqa: E402

import analytics  # noqa: E402
from common import footer, fmt_usd, lang, names, require_data  # noqa: E402
from i18n import t  # noqa: E402

l = lang()
st.title(t("app_title", l))
st.markdown(f"> {t('hook', l)}")
data = require_data()
k = analytics.kpis(data)
y0, y1 = k["first_year"], k["last_year"]

c1, c2, c3, c4 = st.columns(4)
c1.metric(f"{t('k_exports', l)} {y1}", fmt_usd(k["total_exports_usd"], l))
c2.metric(f"{t('k_oil_share', l)} {y1}", analytics._fmt_pct(k["oil_share_last"], l),
          delta=f"{(k['oil_share_last'] - k['oil_share_first']) * 100:+.1f} pp {t('k_vs', l)} {y0}", delta_color="off")
c3.metric(f"{t('k_hhi', l)} {y1}", analytics._fmt_num(k["hhi_product_last"], l),
          delta=f"{k['hhi_product_last'] - k['hhi_product_first']:+,.0f} {t('k_vs', l)} {y0}", delta_color="inverse")
c4.metric(t("k_beta", l), analytics._fmt_num(k["oil_elasticity"], l, 2),
          help="β de ln(exportaciones petroleras) = α + β·ln(Brent)" if l == "es" else "β of ln(oil exports) = α + β·ln(Brent)")

fs = analytics.findings(data, l, names(l))
main = next(f for f in fs if f["id"] == "hhi")
st.subheader(t("main_finding", l))
st.success(f"**{main['title']}** — {main['data']}")

st.subheader(t("all_findings", l))
for f in fs:
    with st.expander(f["title"]):
        st.markdown(f"**{t('f_data', l)}:** {f['data']}\n\n**{t('f_interp', l)}:** {f['interpretation']}\n\n"
                    f"**{t('f_impl', l)}:** {f['implication']}")
footer()
