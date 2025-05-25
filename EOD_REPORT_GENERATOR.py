import streamlit as st
import pandas as pd
from fpdf import FPDF
import smtplib
from email.message import EmailMessage
from datetime import datetime
import os
import base64

# --- Config ---
st.set_page_config(page_title="EOD Banking Report", layout="wide")

BRANCH_MANAGER_EMAILS = {
    "Mumbai": "receiver_mail",
    "Delhi": "receiver_mail",
    "Bangalore": "receiver_mail",
    "Default": "receiver_mail"
}

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_USER = "sender_mail"
EMAIL_PASSWORD = "your app password"  # Keep this safe!

LOAN_TYPES = ['Gold Loan', 'Home Loan', 'Education Loan']

# --- Session State Initialization ---
if "page" not in st.session_state:
    st.session_state.page = "front"
if "uploaded_file" not in st.session_state:
    st.session_state.uploaded_file = None
if "pdf_data" not in st.session_state:
    st.session_state.pdf_data = {}

# --- Functions ---
def reset_state():
    st.session_state.uploaded_file = None
    st.session_state.pdf_data = {}

def generate_pdf_reports(df):
    pdf_data = {}
    grouped = df.groupby("EmployeeID")
    today = datetime.today().strftime("%Y-%m-%d")

    for emp_id, data in grouped:
        name = data['EmployeeName'].iloc[0]
        branch = data['Branch'].iloc[0]
        total_debit = data[data['Type'] == 'Debit']['Amount'].sum()
        total_credit = data[data['Type'] == 'Credit']['Amount'].sum()

        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", "B", 14)
        pdf.cell(200, 10, f"EOD Report - {name} ({emp_id})", ln=True, align="C")
        pdf.set_font("Arial", "", 12)
        pdf.cell(200, 10, f"Date: {today} | Branch: {branch}", ln=True, align="C")
        pdf.ln(10)

        pdf.set_font("Arial", "B", 12)
        pdf.cell(60, 10, f"Total Debits: Rs {total_debit}", ln=False)
        pdf.cell(60, 10, f"Total Credits: Rs {total_credit}", ln=True)
        pdf.ln(5)

        pdf.set_font("Arial", "B", 12)
        pdf.cell(60, 10, "Loan Type", border=1)
        pdf.cell(60, 10, "Paid", border=1)
        pdf.cell(60, 10, "Remaining", border=1)
        pdf.ln()
        pdf.set_font("Arial", "", 12)
        for loan in LOAN_TYPES:
            paid = data[f"{loan} Paid"].sum()
            remaining = data[f"{loan} Remaining"].sum()
            pdf.cell(60, 10, loan, border=1)
            pdf.cell(60, 10, f"Rs {paid}", border=1)
            pdf.cell(60, 10, f"Rs {remaining}", border=1)
            pdf.ln()

        pdf.ln(10)
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, "Transaction History", ln=True)
        pdf.set_font("Arial", "B", 11)
        pdf.cell(40, 10, "Date", border=1)
        pdf.cell(30, 10, "Type", border=1)
        pdf.cell(40, 10, "Amount", border=1)
        pdf.cell(80, 10, "Description", border=1)
        pdf.ln()
        pdf.set_font("Arial", "", 11)

        for _, row in data.iterrows():
            pdf.cell(40, 10, str(row['Date']), border=1)
            pdf.cell(30, 10, str(row['Type']), border=1)
            pdf.cell(40, 10, f"Rs {row['Amount']}", border=1)
            pdf.cell(80, 10, str(row['Description'])[:40], border=1)
            pdf.ln()

        filename = f"EOD_Report_{emp_id}_{today}.pdf"
        pdf.output(filename)

        with open(filename, "rb") as f:
            pdf_bytes = f.read()
        pdf_data[emp_id] = {
            "filename": filename,
            "name": name,
            "branch": branch,
            "pdf_bytes": pdf_bytes
        }
    return pdf_data

def display_pdf(pdf_bytes, filename):
    base64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
    pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="400px" type="application/pdf"></iframe>'
    st.markdown(f"### {filename}", unsafe_allow_html=True)
    st.markdown(pdf_display, unsafe_allow_html=True)
    st.download_button(label="Download PDF", data=pdf_bytes, file_name=filename, mime='application/pdf')

def send_email_report(content, today):
    msg = EmailMessage()
    msg['Subject'] = f"EOD Report - {content['name']} ({today})"
    msg['From'] = EMAIL_USER
    msg['To'] = BRANCH_MANAGER_EMAILS.get(content['branch'], BRANCH_MANAGER_EMAILS['Default'])
    msg.set_content(f"Please find attached the EOD banking report for {content['name']} ({content['branch']} Branch).")
    msg.add_attachment(content['pdf_bytes'], maintype='application', subtype='pdf', filename=content['filename'])

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as smtp:
        smtp.starttls()
        smtp.login(EMAIL_USER, EMAIL_PASSWORD)
        smtp.send_message(msg)

# --- Front Page ---
if st.session_state.page == "front":
    st.title("\U0001F3E6 End-of-Day (EOD) Banking Transaction Report Generator")
    st.markdown(
        """
        #### Your reliable tool for seamless daily banking transaction reports.
        - Upload transaction CSVs
        - Generate detailed PDFs per employee
        - Email reports directly to branch managers
        """
    )
    if st.button("🚀 Start Generating Report"):
        st.session_state.page = "report"
        st.rerun()


# --- Report Page ---
if st.session_state.page == "report":
    st.header("Upload Transaction CSV")
    uploaded_file = st.file_uploader("Upload CSV file with transaction data", type=["csv"], key="upload")
    if uploaded_file is not None:
        st.session_state.uploaded_file = uploaded_file

    if st.session_state.uploaded_file:
        try:
            df = pd.read_csv(st.session_state.uploaded_file)
        except Exception as e:
            st.error(f"Error reading CSV: {e}")
            st.stop()

        required_columns = {'EmployeeID', 'EmployeeName', 'TransactionID', 'Date', 'Amount', 'Type', 'Description', 'Branch'}
        loan_columns = {f"{loan} Paid" for loan in LOAN_TYPES} | {f"{loan} Remaining" for loan in LOAN_TYPES}

        if not required_columns.issubset(df.columns) or not loan_columns.issubset(df.columns):
            st.error(f"CSV missing required columns.\nRequired transaction columns: {required_columns}\nRequired loan columns: {loan_columns}")
            st.stop()

        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("🧮 Generate Report and Preview"):
                with st.spinner("Generating reports..."):
                    st.session_state.pdf_data = generate_pdf_reports(df)
                st.success("✅ Reports generated successfully!")

        with col2:
            if st.button("✅ Send Reports via Email"):
                if not st.session_state.pdf_data:
                    st.warning("Please generate reports before sending emails.")
                else:
                    today = datetime.today().strftime("%Y-%m-%d")
                    all_sent = True
                    for content in st.session_state.pdf_data.values():
                        try:
                            send_email_report(content, today)
                            st.success(f"Email sent to manager for {content['name']}")
                        except Exception as e:
                            st.error(f"Failed to send email for {content['name']}: {e}")
                            all_sent = False
                    if all_sent:
                        st.balloons()

        with col3:
            if st.button("⬅️ Back to Home"):
                reset_state()
                st.session_state.page = "front"
                st.rerun()


        # Display PDFs collapsible
        if st.session_state.pdf_data:
            st.markdown("### Generated PDF Reports:")
            for emp_id, content in st.session_state.pdf_data.items():
                with st.expander(f"{content['name']} (Employee ID: {emp_id}) - Branch: {content['branch']}"):
                    display_pdf(content['pdf_bytes'], content['filename'])

