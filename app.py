import os
import sys
import tempfile
import subprocess
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv


load_dotenv()
st.set_page_config(page_title="DDQ Validator", layout="wide")

st.title("DDQ Validator (Local)")
st.write("Upload a filled DDQ Excel or PDF file.")

with st.sidebar:
    st.header("Inputs")

    filled_file = st.file_uploader(
        "Filled questionnaire (XLSX or PDF)",
        type=["xlsx", "pdf"],
        accept_multiple_files=False
    )
    st.caption("PDF extraction is best-effort; text-based PDFs work best.")

    mode = st.selectbox("Validation mode", options=["LLM (OpenAI)", "Normal (rules only)"])
    llm_model = st.text_input("LLM model", value="gpt-5.2", disabled=(mode != "LLM (OpenAI)"))

    out_dir_name = st.text_input("Output folder name", value="output")
    run_btn = st.button("Validate", type="primary")


if run_btn:
    if not filled_file:
        st.error("Please upload a filled questionnaire XLSX or PDF.")
        st.stop()

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)

        # Save uploaded filled file
        filled_path = tmp_path / f"filled_{filled_file.name}"
        filled_path.write_bytes(filled_file.getbuffer())

        # Output folder (inside temp)
        out_dir = tmp_path / out_dir_name
        out_dir.mkdir(parents=True, exist_ok=True)

        st.info("Running validation…")
        cmd = [
            sys.executable, "-m", "ddq_validator.cli",
            "--filled", str(filled_path),
            "--out-dir", str(out_dir),
        ]
        if mode == "LLM (OpenAI)":
            cmd.extend(["--use-llm", "--llm-model", llm_model])

        # Run the validator
        proc = subprocess.run(cmd, capture_output=True, text=True)

        if proc.returncode != 0:
            st.error("Validator failed.")
            st.code(proc.stdout or "", language="text")
            st.code(proc.stderr or "", language="text")
            st.stop()

        report_csv = out_dir / "report.csv"
        summary_json = out_dir / "summary.json"

        if not report_csv.exists():
            st.error("No report.csv produced. Check validator output below.")
            st.code(proc.stdout or "", language="text")
            st.stop()

        # Show results
        st.success("Validation complete!")

        df = pd.read_csv(report_csv)
        st.subheader("All Items")
        st.dataframe(df, use_container_width=True, height=520)

        # Download buttons
        st.subheader("Downloads")

        st.download_button(
            "Download report.csv",
            data=report_csv.read_bytes(),
            file_name="report.csv",
            mime="text/csv"
        )

        if summary_json.exists():
            st.download_button(
                "Download summary.json",
                data=summary_json.read_bytes(),
                file_name="summary.json",
                mime="application/json"
            )

        # Logs (optional)
        with st.expander("Show validator logs"):
            st.code(proc.stdout or "(no stdout)", language="text")
            st.code(proc.stderr or "(no stderr)", language="text")

