import streamlit as st
import requests
import time

# Streamlit UI setup
st.set_page_config(page_title="📄 AI-Powered PDF Summarizer", layout="wide")

# Apply custom styling for a sleek professional UI
st.markdown("""
    <style>
        body {
            background-color: #282c34; /* Darker background */
            color: #abb2bf; /* Lighter, less harsh text */
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; /* Modern font */
        }
        .stTextInput>div>div>input {
            font-size: 16px;
            padding: 12px;
            border-radius: 8px;
            border: 1px solid #61afef; /* Softer blue */
            background-color: #3e4451; /* Darker input background */
            color: #d1d5db; /* Light gray input text */
        }
        .stButton>button {
            background-color: #61afef; /* Softer blue button */
            color: #ffffff;
            font-size: 18px;
            font-weight: bold;
            padding: 12px 28px;
            border-radius: 8px;
            transition: all 0.3s;
        }
        .stButton>button:hover {
            background-color: #569cd6; /* Slightly darker on hover */
            transform: translateY(-2px);
        }
        .stMarkdown, .stSubheader {
            color: #e06c75; /* Soft red for headers */
            font-weight: bold;
        }
        .summary-section {
            background-color: #3e4451;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            border-left: 5px solid #61afef;
        }
        .section-title {
            color: #61afef;
            font-size: 24px;
            margin-bottom: 15px;
        }        .section-content {
            color: #d1d5db;
            font-size: 16px;
            line-height: 1.6;
        }
        .stTabs [data-baseweb="tab-list"] {
            gap: 24px;
        }
        .stTabs [data-baseweb="tab"] {
            height: 50px;
            padding-left: 20px;
            padding-right: 20px;
            background-color: #3e4451;
            border-radius: 8px;
        }
        .stTabs [aria-selected="true"] {
            background-color: #61afef;
        }
    </style>
""", unsafe_allow_html=True)

# Professional header
st.title("📄 AI-Powered PDF Summarizer")
st.markdown("Extract and summarize research papers with AI-powered efficiency.")

# Add a health check button in the sidebar
with st.sidebar:
    st.markdown("### 🏥 System Status")
    if st.button("🔍 Check Backend Status"):
        try:
            health_response = requests.get("http://localhost:8000/health", timeout=5)
            if health_response.status_code == 200:
                st.success("✅ Backend is running!")
            else:
                st.error("❌ Backend responded with error")
        except requests.exceptions.ConnectionError:
            st.error("❌ Cannot connect to backend")
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")
    
    st.markdown("### 📋 Supported Formats")
    st.markdown("- **URLs:** ArXiv PDF links")
    st.markdown("- **Files:** Local PDF files")
    st.markdown("- **Auto-detection:** Automatic source type detection")

# Add tabs for different input methods
tab1, tab2, tab3 = st.tabs(["🌐 ArXiv URL", "📁 Local File", "🔄 Auto-Detect"])

with tab1:
    st.markdown("### 🔗 Process PDF from ArXiv URL")
    pdf_url = st.text_input("Enter the Arxiv PDF URL:", 
                            placeholder="https://arxiv.org/pdf/2401.02385.pdf",
                            key="url_input")
    
    process_url = st.button("🚀 Summarize from URL", key="url_button")

with tab2:
    st.markdown("### 📁 Process Local PDF File")
    st.markdown("Enter the full path to your PDF file:")
    local_file_path = st.text_input("File Path:", 
                                   placeholder=r"C:\Users\Usuario\Documents\paper.pdf",
                                   key="file_input")
    
    st.markdown("**Examples:**")
    st.code(r"C:\Users\Usuario\Documents\Rains_2004_principios_de_Neuro.pdf")
    st.code(r"D:\Research\Papers\example_paper.pdf")
    
    process_file = st.button("🚀 Summarize Local File", key="file_button")

with tab3:
    st.markdown("### 🔄 Universal Input (Auto-Detection)")
    st.markdown("Enter either a URL or file path - the system will auto-detect:")
    universal_input = st.text_input("URL or File Path:", 
                                   placeholder="https://arxiv.org/pdf/2401.02385.pdf or C:\\path\\to\\file.pdf",
                                   key="universal_input")
    
    st.markdown("**This mode automatically detects whether you're providing:**")
    st.markdown("- 🌐 A URL (starts with http/https)")
    st.markdown("- 📁 A local file path (Windows path format)")
    
    process_universal = st.button("🚀 Smart Summarize", key="universal_button")

# Placeholder for status messages
status_placeholder = st.empty()

def format_section(title, content):
    """Format a section of the summary with consistent styling"""
    return f"""
    <div class="summary-section">
        <div class="section-title">{title}</div>
        <div class="section-content">{content}</div>
    </div>
    """

# Add a spinner and professional feedback system
if process_url or process_file or process_universal:
    # Determine which input to use
    if process_url and pdf_url:
        input_source = pdf_url
        source_type = "url"
        endpoint = "http://localhost:8000/summarize_arxiv/"
        payload = {"url": pdf_url}
        process_description = "ArXiv PDF"
    elif process_file and local_file_path:
        input_source = local_file_path
        source_type = "file"
        endpoint = "http://localhost:8000/summarize_local/"
        payload = {"file_path": local_file_path}
        process_description = "local PDF file"
    elif process_universal and universal_input:
        input_source = universal_input
        source_type = "auto"
        endpoint = "http://localhost:8000/summarize/"
        payload = {"source": universal_input, "source_type": "auto"}
        process_description = "PDF (auto-detected)"
    else:
        if process_url:
            status_placeholder.warning("⚠️ Please enter a valid ArXiv PDF URL.")
        elif process_file:
            status_placeholder.warning("⚠️ Please enter a valid file path.")
        else:
            status_placeholder.warning("⚠️ Please enter a URL or file path.")
        st.stop()
    
    with st.spinner("⏳ Processing... This may take a few minutes."):
        status_placeholder.info(f"⏳ Fetching and summarizing the {process_description}...")
        
        try:
            response = requests.post(
                endpoint,
                json=payload,
                timeout=3600
            )
            
            if response.status_code == 200:
                data = response.json()
                if "error" in data:
                    status_placeholder.error(f"❌ {data['error']}")
                else:                    # Handle different response formats
                    if "final_summary" in data:
                        summary = data["final_summary"]
                        detected_type = data.get("source_type", source_type)
                    else:
                        summary = data.get("summary", "No summary generated.")
                        detected_type = source_type
                    
                    status_placeholder.success("✅ Summary Ready!")
                    
                    # Display source information
                    if source_type == "auto":
                        st.info(f"📄 **Source:** {input_source}")
                        st.success(f"🔍 **Detected Type:** {detected_type}")
                    else:
                        st.info(f"📄 **Source:** {input_source} ({source_type})")
                    
                    # Split the summary into sections and display them
                    sections = summary.split("#")[1:]  # Skip empty first split
                    
                    if sections:
                        for section in sections:
                            if section.strip():
                                # Split section into title and content
                                parts = section.split("\n", 1)
                                if len(parts) == 2:
                                    title, content = parts
                                    st.markdown(
                                        format_section(title.strip(), content.strip()),
                                        unsafe_allow_html=True
                                    )
                    else:
                        # If no sections, display the full summary
                        st.markdown(
                            format_section("Summary", summary),
                            unsafe_allow_html=True
                        )
                    
                    # Add download button for the summary
                    filename = f"summary_{source_type}_{int(time.time())}.md"
                    st.download_button(
                        "⬇️ Download Summary",
                        summary,
                        file_name=filename,
                        mime="text/markdown"
                    )
            else:
                error_detail = ""
                try:
                    error_data = response.json()
                    error_detail = error_data.get("detail", "Unknown error")
                except:
                    error_detail = response.text
                
                status_placeholder.error(f"❌ Failed to process the PDF. Error: {error_detail}")
        except requests.exceptions.Timeout:
            status_placeholder.error("⚠️ Request timed out. Please try again later.")
        except requests.exceptions.ConnectionError:
            status_placeholder.error("❌ Cannot connect to the backend server. Make sure it's running on http://localhost:8000")
        except Exception as e:
            status_placeholder.error(f"⚠️ An error occurred: {str(e)}")

# Add helpful instructions at the bottom
st.markdown("---")
st.markdown("""
### 📝 Usage Instructions:

#### 🌐 **ArXiv URL Mode:**
- Enter any ArXiv PDF URL (e.g., `https://arxiv.org/pdf/2401.02385.pdf`)
- Click "Summarize from URL" to process

#### 📁 **Local File Mode:**
- Enter the full path to your PDF file
- Use Windows path format: `C:\\Users\\Username\\Documents\\file.pdf`
- Make sure the file exists and is a valid PDF
- Click "Summarize Local File" to process

### ⚙️ **Technical Notes:**
- Processing typically takes 3-5 minutes depending on paper length
- Both ArXiv PDFs and local PDF files are supported
- The summary is structured into key sections for better readability
- You can download the summary as a markdown file
- Make sure the backend server is running (`python main.py`)

### 🔧 **Troubleshooting:**
- **Connection Error:** Ensure the backend is running on `http://localhost:8000`
- **File Not Found:** Check that the file path is correct and the file exists
- **Invalid PDF:** Ensure the file is a valid PDF document
- **Timeout:** Large files may take longer to process
""")
