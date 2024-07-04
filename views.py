import json
import os
import re
import cv2
import docx2txt
import fitz
import img2pdf
import numpy as np
import pytesseract
import requests
from PIL import Image
from PyPDF2 import PdfReader
from bs4 import BeautifulSoup
from django.core.files.storage import FileSystemStorage
from django.http import JsonResponse
from django.utils.safestring import mark_safe
from docx import Document
from nltk.stem import PorterStemmer
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from .models import Document, PostingsList
import comtypes.client
from docx2pdf import convert
import os
from django.shortcuts import render
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOCAL_HOST = "http://localhost:8000/"
directory = os.path.join(BASE_DIR, 'files')
stemmer = PorterStemmer()

# Node for a Linked List
class Node:
    """
    This class represents a Linked List node.
    """
    def __init__(self, position):
        """
        This method initializes the linked list with the given position.
        :params:position: Term position in the document
        """
        self.position = position
        self.next = None


# Creating a new node in linked list
def InsertNode(head, position):
    """
    This function inserts a new node with the given position to the linked list.
    :params:head: Head of the lined List node
    :params: position: Position of the term in the document
    :return: head
    """
    node = Node(position)
    # If head is empty, then creating new node else adding a new node
    if head is None:
        return node
    current_node = head

    # assigning the address of the new node to the next of the current node
    while current_node.next:
        current_node = current_node.next
    current_node.next = node
    return head


def document_processing(documents, doc_id):
    """
    This function processes the document and creates a linkedlist for the processed document data.
    :params:document: Document read from the json file
    :return: processed document with positional index
    """
    # Cleaning the data
    preprocessed_doc = [re.sub(r'[^a-zA-Z\s]', '', doc).lower() for doc in documents]

    pos_index = {}
    for document_id, doc in enumerate(preprocessed_doc, start=1):
        # Performing stemming using Porter's stemming
        porter = PorterStemmer()
        terms = [porter.stem(word) for word in doc.split()]
        for pos, term in enumerate(terms, start=1):
            if term not in pos_index:
                pos_index[term] = {}
            if document_id not in pos_index[term]:
                pos_index[term][doc_id] = None
            # calling InsertNode function to insert the document data
            pos_index[term][doc_id] = InsertNode(pos_index[term][doc_id], pos)
    return pos_index


def store_postings(pos_index, output_file, document):
    """
    This function creates a new file and saves the data from the linkedlist to postings.json file
    :params:positional_index: Document data with positional index created by the linked list
    :params:output_file: Name of the output file-postings.json
    """
    json_pos_index = {}
    for term, pos in pos_index.items():
        json_pos = {}
        for document_id, head in pos.items():
            positions = []
            current_node = head
            while current_node:
                # creating position index list
                positions.append(current_node.position)
                current_node = current_node.next
            # assigning the position index to the respective document id
            json_pos[str(document_id)] = positions
        # assigning the position index to the respective term
        json_pos_index[term] = json_pos

    # creating the posting.json file and inserting the doc data
    with open(output_file, 'w') as f:
        json.dump(json_pos_index, f, indent=4)

    # creating the posting.json file and inserting the doc data
    PostingsList.objects.create(document_id=document.id, postings=json_pos_index)


def preprocess(query):
    query = re.sub(r'[^a-zA-Z\s]', '', query).lower()
    terms = query.split()
    terms = [stemmer.stem(term) for term in terms]
    return terms


def find_documents_with_positions(postings, query):
    preprocessed_query = preprocess(query)
    posting_lists = [postings.get(term, {}) for term in preprocessed_query]

    # Find intersection of posting lists
    intersection = set(posting_lists[0].keys())
    for posting_list in posting_lists[1:]:
        intersection.intersection_update(posting_list.keys())

    results = []
    for document in intersection:
        positions = []
        for term in preprocessed_query:
            positions.append(postings[term].get(document, []))

        # Flatten the list of positions
        flattened_positions = [position if isinstance(position, list) else [position] for position in positions]

        # Check if query terms occur consecutively
        for i in range(len(flattened_positions[0])):
            start_position = flattened_positions[0][i]
            if all(start_position + idx in position_set for idx, position_set in
                   enumerate(flattened_positions[1:], start=1)):
                results.append((document, start_position))

    return results


def text_from_url( url):
    """
    Extract text from URL
    :param url: URL
    :return: extracted text
    """
    try:
        response = requests.get(url)
        if response.status_code == 200:
            b_soup = BeautifulSoup(response.content, 'html.parser')
            # Extract text from the webpage
            text = b_soup.get_text()
            # Remove extra whitespaces and newlines
            text = re.sub(r'\s+', ' ', text)
            return text
        else:
            print("Couldn't fetch content from URL.")
            return None
    except Exception as e:
        print("Error:", e)
        return None


def text_from_docx(file_path):
    """
    Extract text from word doc
    :param file_path: path of local file
    :return: text
    """
    text = docx2txt.process(file_path)
    return text


def img_to_text(img_path):
    """
    Extract text from image
    :param img_path: local image file path
    :return: text
    """
    pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    img = Image.open(img_path)
    img = img.convert('L')
    img = np.array(img)
    _, img = cv2.threshold(img, 128, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
    txt = pytesseract.image_to_string(img)
    return txt


def home(request):
    """
    Renders home page
    :param request:
    :return: home page
    """
    return render(request, 'home.html')


def upload_document(request):
    """
    This function uploads all types of documents
    :param request: request
    :return: Successfully uploads the file
    """
    if request.method == 'POST':
        file_inp = []
        try:
            for file_type in ['pdf-upload', 'doc-upload', 'txt-upload', 'img-upload']:
                for file in request.FILES.getlist(file_type):
                    file_inp.append(file)
        except:
            file_inp = request.POST.getlist('url')
            file_type = "url"

        message = ""
        existing_files = []
        uploaded_files = []
        for file in file_inp:
            file_type = str(file).split('.')[1]
            file_name = str(file).split('.')[0]
            f_content = extract_text_content(file, file_type)
            if Document.objects.filter(content=f_content).exists():
                existing_files.append(file_name)
            else:
                uploaded_files.append(file_name)

            existing_files_message = ", ".join(existing_files) + " already exists." if existing_files else ""
            uploaded_files_message = ", ".join(uploaded_files) + " uploaded." if uploaded_files else ""

            message = existing_files_message + " " + uploaded_files_message
            if file_name not in existing_files:
                fs = FileSystemStorage()
                filename = fs.save(file, file)
                file_url = fs.url(filename)
                document = Document.objects.create(title=file_name, content=f_content, file_type=file_type)
                # Process document and create positional index
                pos_index = document_processing([f_content], document.id)
                # Save positional index to a file
                store_postings(pos_index, 'postings.json', document)
            else:
                continue
        return render(request, 'home.html',{'data': message})

    return render(request, 'upload_document.html')


def extract_text_content(file, file_type):
    """
    Extract content from various file types
    :param file: file
    :param file_type: file type
    :return: text
    """
    text = ""
    if file_type == 'pdf':
        pdf_reader = PdfReader(file)
        cont = ''
        for page in pdf_reader.pages:
            cont += page.extract_text()
        return cont

    elif file_type in ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff', 'svg', 'webp', 'ico']:
        text = img_to_text(file)

    elif file_type == "url":
        text = text_from_url(file)

    elif file_type == 'docx':
        text = text_from_docx(file)
    else:
        return file.read().decode('utf-8')
    return text


def highlight_words_in_pdf(pdf_path, highlight_words):
    """
    This function highlights queries in pdf
    :param pdf_path: local pdf file
    :param highlight_words: queries
    :return: pdf doc
    """
    pdf_document = fitz.open(pdf_path)

    # Looping through each page
    for page_number in range(len(pdf_document)):
        page = pdf_document[page_number]
        # get text
        page_text = page.get_text()

        # Check if any of the words are present
        for word in highlight_words:
            # Search the word
            text_inst = page.search_for(word)
            # highlight each instance
            for inst in text_inst:
                highlight = page.add_highlight_annot(inst)

    # save pdf
    h_pdf_path = pdf_path.replace('.pdf', '_highlighted.pdf')
    pdf_document.save(h_pdf_path)

    # Close the PDF document
    pdf_document.close()

    return h_pdf_path


def convert_docx_to_pdf(input_path, output_path):
    """
    This fucntion converts a DOCX file to a PDF
    :param input_path: local file path
    :param output_path: pdf file path
    :return: pdf file
    """
    comtypes.CoInitialize()
    convert(input_path, output_path)


def text_to_pdf(text_path, pdf_file_path):
    """
    This function converts text file to pdf
    :param text_path: local text file path
    :param pdf_file_path: pdf file path
    :return: pdf file
    """
    pdf_can = canvas.Canvas(pdf_file_path, pagesize=letter)

    # Open the text file
    with open(text_path, 'r') as text_file:
        textlines = text_file.readlines()

    x = 72
    y = letter[1] - 72

    for line in textlines:
        pdf_can.drawString(x, y, line.strip())
        y -= 12

        if y < 72:
            pdf_can.showPage()
            y = letter[1] - 72
    pdf_can.save()


def img_to_pdf(img_path, pdf_path):
    """
    This function converts image file to pdf
    :param img_path: local image file path
    :param pdf_path: pdf file path
    :return: pdf file
    """
    img = Image.open(img_path)
    # converting the image to PDF bytes
    pdf_byt = img2pdf.convert(img.filename)
    with open(pdf_path, "wb") as pdf_file:
        pdf_file.write(pdf_byt)


def search_documents(request):
    """
    This function searches the query enetered by the user in the documents and return the original documents
    :param request: request
    :return: documents containing the query
    """
    if request.method == "POST":
        query = request.POST.get('q')
        if query:
            queries = query.split(';')
            postings = list(PostingsList.objects.all().values_list("postings"))
            file_urls = dict()
            for query in queries:
                for posting in postings:
                    print("Query:", query)
                    results = find_documents_with_positions(posting[0], query)
                    if results:
                        document_id = int(results[0][0])
                        doc_obj = Document.objects.get(id=document_id)
                        file_name = doc_obj.title
                        file_type = doc_obj.file_type
                        file_path = os.path.join(LOCAL_HOST, 'media', file_name + '.' + file_type)
                        current_file_path = os.path.join(BASE_DIR, 'media', file_name + '.' + file_type)
                        file_path.replace("\\", "//")

                        # highlight documents according to file types
                        if file_type == 'pdf':
                            highlighted_pdf_path = highlight_words_in_pdf(current_file_path, queries)
                        elif file_type == 'docx':
                            convert_docx_to_pdf(current_file_path,
                                                os.path.join(BASE_DIR, 'media', file_name + '.' + 'pdf'))
                            current_file_path = os.path.join(BASE_DIR, 'media', file_name + '.' + 'pdf')
                            highlighted_pdf_path = highlight_words_in_pdf(current_file_path, queries)
                        elif file_type == 'txt':
                            text_to_pdf(current_file_path,
                                                os.path.join(BASE_DIR, 'media', file_name + '.' + 'pdf'))
                            current_file_path = os.path.join(BASE_DIR, 'media', file_name + '.' + 'pdf')
                            highlighted_pdf_path = highlight_words_in_pdf(current_file_path, queries)
                        elif file_type in ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff', 'svg', 'webp', 'ico']:
                            img_to_pdf(current_file_path,
                                             os.path.join(BASE_DIR, 'media', file_name + '.' + 'pdf'))
                            current_file_path = os.path.join(BASE_DIR, 'media', file_name + '.' + 'pdf')
                            highlighted_pdf_path = highlight_words_in_pdf(current_file_path, queries)
                        local_file_path = os.path.join(LOCAL_HOST, 'media', highlighted_pdf_path.split('\\')[-1]).replace("\\", "//")
                        file_urls[file_name] = local_file_path
                    else:
                        print("No documents found.")

            for key, value in file_urls.items():
                file_urls[key] = value.replace("\\", "/")
            return render(request, 'results.html', {'results': results, 'file_urls': file_urls, 'query_terms': query})

    return render(request, 'home.html')
