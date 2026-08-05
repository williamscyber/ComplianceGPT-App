import os
import streamlit as st
import xml.etree.ElementTree as ET
from huggingface_hub import InferenceClient
from sklearn.feature_extraction.text import TfidfVectorizer

MODEL_NAME = "google/gemma-4-31B-it"
XML_PATH = "title-45.xml"

# =====================================================
# XML LOADING
# =====================================================

def get_text(element):
    if element is None:
        return ""
    return "".join(element.itertext()).strip()


def load_hipaa_xml(xml_path):
    tree = ET.parse(xml_path)
    root = tree.getroot()

    sections = []

    for section in root.iter():
        if section.attrib.get("TYPE") != "SECTION":
            continue

        section_number = section.attrib.get("N", "Unknown")
        section_title = get_text(section.find("HEAD"))

        paragraphs = []
        for p in section.findall("./P"):
            text = get_text(p)
            if text:
                paragraphs.append(text)

        full_text = "\n".join(paragraphs)

        sections.append({
            "section": section_number,
            "title": section_title,
            "text": full_text,
        })

    return sections


hipaa_data = load_hipaa_xml(XML_PATH)

# =====================================================
# VECTORIZATION (RAG)
# =====================================================

vectorizer = TfidfVectorizer(stop_words="english")

tfidf_matrix = vectorizer.fit_transform(
    [section["text"] for section in hipaa_data]
)

# =====================================================
# HF CLIENT
# =====================================================

def get_client():
    return InferenceClient(
        model=MODEL_NAME,
        token=os.environ["HF_TOKEN"]
    )
# def get_client():
#     return InferenceClient(
#         provider="novita",
#         model="MiniMaxAI/MiniMax-M2.1",
#         token=os.environ["HF_TOKEN"]
#     )

# =====================================================
# RETRIEVAL
# =====================================================

def retrieve_sections(query, k=3):
    query_vector = vectorizer.transform([query])

    similarity = (tfidf_matrix @ query_vector.T).toarray().flatten()
    top_indices = similarity.argsort()[-k:][::-1]

    retrieved_text = ""
    sources = []

    for i in top_indices:
        sec = hipaa_data[i]

        retrieved_text += f"""
Section: {sec['section']}
Title: {sec['title']}
Text: {sec['text']}
----------------------------------------
"""
        sources.append(f"§ {sec['section']} - {sec['title']}")

    return retrieved_text, sources

# =====================================================
# BASELINE
# =====================================================

def baseline_answer(question):
    client = get_client()

    response = client.chat_completion(
        messages=[
            {
                "role": "system",
                "content": """
You are a HIPAA compliance expert.

Analyze the scenario carefully.

You MUST:
- Consider both arguments FOR and AGAINST disclosure.
- Do not default to denial.
- Only say "DENIED" if clearly prohibited.
- Say "PERMITTED" if disclosure could be permitted under specific conditions.

Format:

Verdict: <PERMITTED / DENIED>

Explanation: <Balanced reasoning>

Citations: <Relevant HIPAA sections. Section number only.>
"""
            },
            {"role": "user", "content": question}
        ],
        max_tokens=800
    )

    return response.choices[0].message.content

# =====================================================
# RAG (XML ONLY)
# =====================================================

def rag_answer(question):
    retrieved_text, sources = retrieve_sections(question)

    client = get_client()

    response = client.chat_completion(
        messages=[
            {
                "role": "system",
                "content": f"""
You are a HIPAA compliance expert.

You MUST answer ONLY using the HIPAA sections below.

Retrieved HIPAA Sections:

{retrieved_text}

Rules:

- Use ONLY the retrieved sections.
- Do NOT invent citations.
- If the answer is not supported by the retrieved text, say:
  "Not explicitly stated in the provided HIPAA sections."
- Do not default to denying disclosure.
- Give balanced reasoning.

Format:

Verdict: <PERMITTED / DENIED>

Explanation: <Short summary of reasoning based only on the retrieved sections>

Citations: <Section numbers only. ONLY output the ciation number.>
"""
            },
            {"role": "user", "content": question}
        ],
        max_tokens=800
    )

    return response.choices[0].message.content, sources

# =====================================================
# AGENTIC
# =====================================================

def extractor_agent(question):
    client = get_client()

    response = client.chat_completion(
        messages=[
            {
                "role": "system",
                "content": """
You are the Extractor Agent.

Extract:

- HIPAA topic
- Entities involved
- Action performed
- Compliance issue

Keep it concise.
"""
            },
            {"role": "user", "content": question}
        ],
        max_tokens=800
    )

    return response.choices[0].message.content


def verdict_agent(question, extracted, sources_text):
    client = get_client()

    response = client.chat_completion(
        messages=[
            {
                "role": "system",
                "content": """
You are a HIPAA compliance expert.

Use ONLY provided HIPAA XML context.
Do NOT hallucinate citations.
If unsure → say UNKNOWN.

Format EXACTLY:

Verdict: PERMITTED or DENIED or UNKNOWN

Explanation:

Citations:
"""
            },
            {
                "role": "user",
                "content": f"""
Question:
{question}

Extracted:
{extracted}

HIPAA Sources:
{sources_text}
"""
            }
        ],
        max_tokens=800
    )

    return response.choices[0].message.content


def agentic_answer(question):
    extracted = extractor_agent(question)

    # retrieval based on extracted structure
    sources_text, sources = retrieve_sections(extracted)

    verdict = verdict_agent(question, extracted, sources_text)

    return extracted, sources, verdict

# =====================================================
# STREAMLIT UI
# =====================================================

st.title("HIPAA Compliance Assistant")

st.caption(f"Current Model: {MODEL_NAME}")

st.write(
    "Ask any HIPAA compliance question using different reasoning frameworks."
)

framework = st.selectbox(
    "Choose Framework",
    [
        "Baseline",
        "RAG",
        "Agentic"
    ]
)

mode = st.selectbox(
    "Choose Interaction Mode",
    [
        "Single Q&A",
        "Chat"
    ]
)

if "history" not in st.session_state:
    st.session_state.history = []

if st.button("Clear Chat & History"):
    st.session_state.history = []

# =====================================================
# INPUT
# =====================================================

if prompt := st.chat_input("Ask a HIPAA question..."):

    if mode == "Single Q&A":

        if framework == "Baseline":
            st.write(baseline_answer(prompt))

        elif framework == "RAG":
            answer, sources = rag_answer(prompt)
            st.write(answer)

            st.subheader("Sources")
            for s in sources:
                st.write(s)

        elif framework == "Agentic":
            extracted, sources, verdict = agentic_answer(prompt)

            st.subheader("Extractor Output")
            st.write(extracted)

            st.subheader("Retrieved Sources")
            for s in sources:
                st.write(s)

            st.subheader("Final Verdict")
            st.write(verdict)

    else:
        st.session_state.history.append({"role": "user", "content": prompt})

        with st.chat_message("user"):
            st.write(prompt)

        if framework == "Baseline":
            reply = baseline_answer(prompt)

        elif framework == "RAG":
            reply, _ = rag_answer(prompt)

        else:
            extracted, sources, verdict = agentic_answer(prompt)
            reply = f"{verdict}\n\n---\n\n{extracted}"

        st.session_state.history.append({"role": "assistant", "content": reply})

        with st.chat_message("assistant"):
            st.write(reply)