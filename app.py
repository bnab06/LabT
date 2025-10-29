# -------------------------
# Helper fig->bytes
# -------------------------
def fig_to_bytes(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    buf.seek(0)
    return buf

# -------------------------
# Linearity panel
# -------------------------
def linearity_panel():
    st.header(t("linearity"))
    company = st.text_input(t("company"), key="company_name")

    mode = st.radio("Input mode", [t("input_csv"), t("input_manual")], key="lin_input_mode")
    df = None

    if mode == t("input_csv"):
        uploaded = st.file_uploader("Upload CSV with two columns (concentration, signal)", type=["csv"], key="lin_csv")
        if uploaded:
            try:
                uploaded.seek(0)
                df0 = pd.read_csv(uploaded)
                cols_low = [c.lower() for c in df0.columns]
                if "concentration" in cols_low and "signal" in cols_low:
                    df = df0.rename(columns={df0.columns[cols_low.index("concentration")]: "Concentration",
                                             df0.columns[cols_low.index("signal")]: "Signal"})
                elif len(df0.columns) >= 2:
                    df = df0.iloc[:, :2].copy()
                    df.columns = ["Concentration","Signal"]
                else:
                    st.error("CSV must contain at least two columns (concentration, signal).")
                    df = None
            except Exception as e:
                st.error(f"CSV error: {e}")
                df = None
    else:
        st.caption("Enter concentrations (comma-separated) and signals (comma-separated).")
        cols = st.columns(2)
        conc_input = cols[0].text_area("Concentrations (comma separated)", height=120, key="lin_manual_conc")
        sig_input = cols[1].text_area("Signals (comma separated)", height=120, key="lin_manual_sig")
        if st.button("Load manual pairs"):
            try:
                concs = [float(c.replace(",",".").strip()) for c in conc_input.split(",") if c.strip()!=""]
                sigs = [float(s.replace(",",".").strip()) for s in sig_input.split(",") if s.strip()!=""]
                if len(concs) != len(sigs):
                    st.error("Number of concentrations and signals must match.")
                elif len(concs) < 2:
                    st.warning("At least two pairs are required.")
                else:
                    df = pd.DataFrame({"Concentration":concs, "Signal":sigs})
            except Exception as e:
                st.error(f"Manual parse error: {e}")

    unit = st.selectbox(t("unit"), ["µg/mL","mg/mL","ng/mL"], index=0, key="lin_unit")

    if df is None:
        st.info("Please provide data (CSV or manual).")
        return

    try:
        df["Concentration"] = pd.to_numeric(df["Concentration"])
        df["Signal"] = pd.to_numeric(df["Signal"])
    except Exception:
        st.error("Concentration and Signal must be numeric.")
        return

    if len(df) < 2:
        st.warning("At least 2 points are required.")
        return

    # Fit linear regression
    coeffs = np.polyfit(df["Concentration"].values, df["Signal"].values, 1)
    slope = float(coeffs[0])
    intercept = float(coeffs[1])
    y_pred = np.polyval(coeffs, df["Concentration"].values)
    ss_res = np.sum((df["Signal"].values - y_pred)**2)
    ss_tot = np.sum((df["Signal"].values - np.mean(df["Signal"].values))**2)
    r2 = float(1 - ss_res/ss_tot) if ss_tot != 0 else 0.0

    st.session_state.linear_slope = slope

    st.metric("Slope", f"{slope:.6f}")
    st.metric("Intercept", f"{intercept:.6f}")
    st.metric("R²", f"{r2:.4f}")

    fig, ax = plt.subplots(figsize=(7,3))
    ax.scatter(df["Concentration"], df["Signal"], label="Data")
    xs = np.linspace(df["Concentration"].min(), df["Concentration"].max(), 120)
    ax.plot(xs, slope*xs + intercept, color="red", label="Fit")
    ax.set_xlabel(f"{t('concentration')} ({unit})")
    ax.set_ylabel(t("signal"))
    ax.legend()
    st.pyplot(fig)

    # Compute automatically
    st.subheader("Calcul automatique")
    df["Calc_Signal"] = slope*df["Concentration"] + intercept
    st.dataframe(df)

    # Export CSV
    csv_buf = io.StringIO()
    df.to_csv(csv_buf, index=False)
    st.download_button(t("download_csv"), csv_buf.getvalue(), file_name="linearity.csv", mime="text/csv")

    # Export PDF only if company name provided
    if st.button(t("generate_pdf")):
        if not company.strip():
            st.warning(t("company_missing"))
        else:
            pdf_lines = [f"{t('company')}: {company}"]
            pdf_lines.append(f"Slope: {slope:.6f}")
            pdf_lines.append(f"Intercept: {intercept:.6f}")
            pdf_lines.append(f"R²: {r2:.4f}")
            pdf_bytes = generate_pdf_bytes("Linearity Report", pdf_lines, img_bytes=fig_to_bytes(fig), logo_path=LOGO_FILE)
            st.download_button(t("download_pdf"), pdf_bytes, file_name="linearity.pdf", mime="application/pdf")

# -------------------------
# S/N Panel
# -------------------------
def sn_panel():
    st.header(t("sn"))
    uploaded = st.file_uploader(t("upload_chrom"), type=["csv","png","jpg","jpeg","pdf"], key="sn_file")
    df = None

    if uploaded:
        name = uploaded.name.lower()
        if name.endswith(".csv"):
            try:
                uploaded.seek(0)
                df0 = pd.read_csv(uploaded)
                if df0.shape[1] < 2:
                    st.error("CSV must have at least two columns")
                    return
                df = df0.iloc[:, :2]
                df.columns = ["Time","Signal"]
            except Exception as e:
                st.error(f"CSV read error: {e}")
                return
        elif name.endswith((".png",".jpg",".jpeg")):
            img = Image.open(uploaded)
            df = extract_xy_from_image_pytesseract(img)
        elif name.endswith(".pdf") and convert_from_bytes is not None:
            try:
                pages = convert_from_bytes(uploaded.read(), dpi=200)
                img = pages[0]
                df = extract_xy_from_image_pytesseract(img)
            except Exception as e:
                st.error(f"PDF read error: {e}")
                return
        else:
            st.warning("Unsupported format or OCR unavailable.")
            return

        if df is None or df.empty:
            st.warning("No data extracted")
            return

        st.write(df.head())
        col_min, col_max = st.columns(2)
        min_val = float(df["Time"].min())
        max_val = float(df["Time"].max())
        region = st.slider(t("select_region"), min_val, max_val, (min_val, max_val), key="sn_region")

        # Filter
        df_sel = df[(df["Time"] >= region[0]) & (df["Time"] <= region[1])].copy()
        if df_sel.empty:
            st.warning("No points in selected region")
            return

        # Compute S/N classic
        sn_classic = df_sel["Signal"].max() / df_sel["Signal"].std() if df_sel["Signal"].std()!=0 else 0
        # Compute USP
        try:
            h = df_sel["Signal"].max() - df_sel["Signal"].min()
            sigma = df_sel["Signal"].std()
            sn_usp = h / sigma if sigma != 0 else 0
        except:
            sn_usp = 0
        # LOD/LOQ from slope
        slope = st.session_state.linear_slope or 1.0
        lod = 3*df_sel["Signal"].std()/slope
        loq = 10*df_sel["Signal"].std()/slope

        st.metric(t("sn_classic"), f"{sn_classic:.3f}")
        st.metric(t("sn_usp"), f"{sn_usp:.3f}")
        st.metric(t("lod"), f"{lod:.6f}")
        st.metric(t("loq"), f"{loq:.6f}")

        fig, ax = plt.subplots(figsize=(7,3))
        ax.plot(df["Time"], df["Signal"], label="Full")
        ax.plot(df_sel["Time"], df_sel["Signal"], color="red", label="Selected")
        ax.set_xlabel("Time")
        ax.set_ylabel("Signal")
        ax.legend()
        st.pyplot(fig)

        # Export CSV
        csv_buf = io.StringIO()
        df_sel.to_csv(csv_buf, index=False)
        st.download_button(t("download_csv"), csv_buf.getvalue(), file_name="sn_region.csv", mime="text/csv")

        # Export PDF
        pdf_lines = [
            f"S/N Classic: {sn_classic:.3f}",
            f"S/N USP: {sn_usp:.3f}",
            f"LOD: {lod:.6f}",
            f"LOQ: {loq:.6f}"
        ]
        pdf_bytes = generate_pdf_bytes("S/N Report", pdf_lines, img_bytes=fig_to_bytes(fig), logo_path=LOGO_FILE)
        st.download_button(t("export_sn_pdf"), pdf_bytes, file_name="sn_report.pdf", mime="application/pdf")

# -------------------------
# Main app
# -------------------------
def main():
    if st.session_state.user is None:
        login_screen()
        return

    # Horizontal tabs instead of sidebar
    tabs = st.tabs([t("linearity"), t("sn"), t("admin")])
    with tabs[0]:
        linearity_panel()
    with tabs[1]:
        sn_panel()
    with tabs[2]:
        if st.session_state.role != "admin":
            st.warning("Admin only")
        else:
            admin_panel()

if __name__ == "__main__":
    main()