import streamlit as st
import os
import tempfile
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import base64
from io import BytesIO
from PIL import Image
import numpy as np

# Import our DocumentAnalyzer class
# Make sure to place the DocumentAnalyzer class in a separate file named document_analyzer.py
# or copy the class implementation here
from document_analyzer import DocumentAnalyzer

# Set page config
st.set_page_config(
    page_title="Document Analyzer",
    page_icon="📄",
    layout="wide",
)

# Title and description
st.title("Document Content Analyzer")
st.markdown("""
This application analyzes PDF and Word documents to extract information about:
- Text content and statistics
- Images (count, size, type)
- Color analysis (colored vs. grayscale vs. black & white)
""")

# File uploader
uploaded_file = st.file_uploader("Upload a PDF or Word document", type=["pdf", "docx"])

# Function to create a downloadable link for plot
def get_image_download_link(fig, filename, text):
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=300, bbox_inches='tight')
    buf.seek(0)
    b64 = base64.b64encode(buf.read()).decode()
    href = f'<a href="data:image/png;base64,{b64}" download="{filename}">📥 {text}</a>'
    return href

# Display dominant colors
def display_color_palette(colors):
    if not colors:
        return None
    
    # Extract RGB values and counts
    rgb_values = [color['rgb'] for color in colors]
    counts = [color['count'] for color in colors]
    
    # Normalize counts to get percentages
    total = sum(counts)
    percentages = [count/total for count in counts]
    
    # Create a figure for the color palette
    fig, ax = plt.subplots(figsize=(10, 2))
    
    # Create color bars
    start = 0
    for i, (rgb, percentage) in enumerate(zip(rgb_values, percentages)):
        # Convert BGR to RGB (OpenCV uses BGR)
        r, g, b = rgb
        color = (r/255, g/255, b/255)
        
        end = start + percentage
        ax.barh(0, percentage, left=start, color=color, height=1)
        
        # Add percentage label if it's significant enough
        if percentage > 0.05:  # Only show label if it's more than 5%
            text_x = start + percentage/2
            ax.text(text_x, 0, f"{percentage:.1%}", 
                    ha='center', va='center', 
                    color='white' if sum(rgb) < 380 else 'black',
                    fontweight='bold')
        
        start = end
    
    ax.set_xlim(0, 1)
    ax.set_ylim(-0.5, 0.5)
    ax.axis('off')
    
    return fig

if uploaded_file is not None:
    # Display a spinner while processing
    with st.spinner('Analyzing document...'):
        # Save the uploaded file to a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1]) as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            tmp_filepath = tmp_file.name
        
        try:
            # Initialize the analyzer
            analyzer = DocumentAnalyzer()
            
            # Analyze the document
            results = analyzer.analyze_document(tmp_filepath)
            
            # Clean up the temporary file
            os.unlink(tmp_filepath)
            
            # Display results in tabs
            tab1, tab2, tab3 = st.tabs(["Document Info", "Text Analysis", "Image Analysis"])
            
            with tab1:
                st.header("Document Information")
                col1, col2 = st.columns(2)
                
                with col1:
                    st.metric("Document Type", results['document_type'])
                    st.metric("Page Count", results['page_count'])
                    st.metric("Total Words", results['text_analysis']['word_count'])
                
                with col2:
                    st.metric("Total Characters", results['text_analysis']['char_count'])
                    st.metric("Paragraphs", results['text_analysis']['paragraph_count'])
                    st.metric("Images", results['image_analysis']['image_count'])
            
            with tab2:
                st.header("Text Analysis")
                
                # Word count visualization
                st.subheader("Text Statistics")
                text_data = {
                    'Metric': ['Words', 'Characters', 'Paragraphs'],
                    'Count': [
                        results['text_analysis']['word_count'],
                        results['text_analysis']['char_count'],
                        results['text_analysis']['paragraph_count']
                    ]
                }
                
                fig, ax = plt.subplots(figsize=(10, 5))
                sns.barplot(x='Metric', y='Count', data=pd.DataFrame(text_data), palette='viridis')
                ax.set_title('Document Text Statistics')
                st.pyplot(fig)
                
                # Provide download link for the plot
                st.markdown(get_image_download_link(fig, "text_stats.png", "Download Text Statistics Chart"), unsafe_allow_html=True)
                
                # Display text sample
                st.subheader("Text Sample (first 500 characters)")
                text_sample = analyzer.text_content[:500] + "..." if len(analyzer.text_content) > 500 else analyzer.text_content
                st.text_area("", text_sample, height=200)
            
            with tab3:
                st.header("Image Analysis")
                
                # Image color chart
                color_summary = results['image_analysis']['color_summary']
                
                if results['image_analysis']['image_count'] > 0:
                    st.subheader("Image Color Distribution")
                    
                    color_data = {
                        'Type': ['Color', 'Grayscale', 'Black & White'],
                        'Count': [
                            color_summary['color'],
                            color_summary['grayscale'],
                            color_summary['black_white']
                        ]
                    }
                    
                    fig, ax = plt.subplots(figsize=(10, 5))
                    colors = ['#ff9999', '#66b3ff', '#99ff99']
                    
                    bars = sns.barplot(x='Type', y='Count', data=pd.DataFrame(color_data), palette=colors)
                    
                    # Add percentage labels on top of each bar
                    total = sum(color_data['Count'])
                    for i, p in enumerate(bars.patches):
                        percentage = 100 * color_data['Count'][i] / total if total > 0 else 0
                        bars.annotate(f'{percentage:.1f}%', 
                                    (p.get_x() + p.get_width() / 2., p.get_height()), 
                                    ha='center', va='bottom', fontsize=12)
                    
                    ax.set_title('Image Color Distribution')
                    st.pyplot(fig)
                    
                    # Provide download link for the plot
                    st.markdown(get_image_download_link(fig, "image_color_chart.png", "Download Image Color Chart"), unsafe_allow_html=True)
                    
                    # Display image info in a table
                    st.subheader("Image Information")
                    image_data = [
                        {
                            'Index': img['index'] + 1,
                            'Dimensions': img['dimensions'],
                            'Format': img['format'].upper(),
                            'Page': img.get('page', 'N/A')
                        } for img in results['image_analysis']['images']
                    ]
                    
                    st.dataframe(pd.DataFrame(image_data), use_container_width=True)
                    
                    # Display dominant colors if available
                    if 'dominant_colors' in results['image_analysis'] and results['image_analysis']['dominant_colors']:
                        st.subheader("Dominant Colors")
                        
                        for color_info in results['image_analysis']['dominant_colors']:
                            st.markdown(f"**Image #{color_info['image_index'] + 1}**")
                            fig = display_color_palette(color_info['colors'])
                            if fig:
                                st.pyplot(fig)
                else:
                    st.info("No images found in the document.")
                
        except Exception as e:
            st.error(f"Error analyzing document: {str(e)}")
else:
    # Display sample results with dummy data
    st.info("👆 Upload a document to analyze its content")
    
    # Show a sample analysis with dummy data
    with st.expander("See sample analysis"):
        st.markdown("""
        ### Sample Document Analysis
        
        This is how your results will appear after uploading a document.
        
        #### Document Information:
        - **Document Type:** PDF
        - **Page Count:** 5
        - **Word Count:** 2,500
        - **Character Count:** 15,000
        - **Image Count:** 8
        
        #### Image Analysis:
        - **Color Images:** 5 (62.5%)
        - **Grayscale Images:** 2 (25%)
        - **Black & White Images:** 1 (12.5%)
        """)
        
        # Create a sample chart
        fig, ax = plt.subplots(figsize=(10, 5))
        sample_data = pd.DataFrame({
            'Type': ['Color', 'Grayscale', 'Black & White'],
            'Count': [5, 2, 1]
        })
        sns.barplot(x='Type', y='Count', data=sample_data, palette=['#ff9999', '#66b3ff', '#99ff99'])
        ax.set_title('Sample Image Color Distribution')
        st.pyplot(fig)