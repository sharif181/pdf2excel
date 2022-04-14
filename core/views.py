import os
from django.shortcuts import render
import pdfplumber
from django.core.files.storage import default_storage
from django.core.files.storage import FileSystemStorage
import csv
import tabula
from PIL import Image


# Create your views here.

def home(request):
    if request.method == "POST":
        pdf = request.FILES.get("pdf_file", None)
        image = request.FILES.get("image_file", None)
        if pdf:
            file_name = default_storage.save(pdf.name, pdf)
            links = get_pdf_data(file_name)
            file_url = []
            for link in links:
                file_url.append(f"http://127.0.0.1:8000/media/{link}")
            default_storage.delete(file_name)
            return render(request, 'index.html', {"table_url": file_url[0], "other_url": file_url[1]})
        elif image:
            print('image')
    return render(request, 'index.html')


def set_row(line, type, key, split_by):
    row = {}
    row["Type"] = type
    row["Key"] = key
    row["Value"] = line.split(split_by)[-1]
    return row


def get_pdf_data(pdf_file):
    result = []
    try:
        df = tabula.read_pdf(f"./media/{pdf_file}", pages='all')[0]
        csv_file = f"./media/result_lineitems.csv"
        df = df.iloc[:-1, :]
        df.rename(columns={'Description': 'items', 'Qty': 'quantity', 'Amount GBP': 'price'}, inplace=True)
        df.to_csv(csv_file)

        with pdfplumber.open(f"./media/{pdf_file}") as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                for line in text.split('\n'):
                    if "Trading Company:" in line:
                        result.append(set_row(line, "VENDOR_NAME", "", ":"))
                        result.append(set_row(line, "OTHER", "Trading Company", ":"))
                        row = {}
                        row["Type"] = "RECEIVER_ADDRESS"
                        row["Key"] = "Delivery Address"
                        row["Value"] = line.rpartition('Trading Company:')[0]
                        result.append(row)
                    if "Supplier ID:" in line:
                        result.append(set_row(line, "OTHER", "Supplier ID:", ":"))
                    if "Page" in line:
                        result.append(set_row(line, "OTHER", "Page", " "))
                    if "Agreement Ref:" in line:
                        result.append(set_row(line, "OTHER", "Agreement Ref:", ":"))
                        row = {}
                        row["Type"] = "OTHER"
                        row["Key"] = "Supplier Information"
                        row["Value"] = line.rpartition('Agreement Ref:')[0]
                        result.append(row)
                    if "Requisition:" in line:
                        result.append(set_row(line, "OTHER", "Requisition:", ":"))
                    if "Input by:" in line:
                        result.append(set_row(line, "OTHER", "Input by:", ":"))
                    if "STANDARD PURCHASE ORDER NUMBER:" in line:
                        result.append(set_row(line, "OTHER", "STANDARD PURCHASE ORDER NUMBER:", ":"))
                        result.append(set_row(line, "OTHER", "Please quote order number", ":"))
                    if "Order Total GBP" in line:
                        result.append(set_row(line, "TOTAL", "Order Total GBP", " "))
                    if "Order Date:" in line:
                        result.append(set_row(line, "INVOICE_RECEIPT_DATE", "Order Date:", ":"))
                    if "Payment Terms:" in line:
                        result.append(set_row(line, "PAYMENT_TERMS", "Payment Terms:", ':'))
                    if "Requested by:" in line:
                        result.append(set_row(line, "OTHER", "Requested By:", ":"))

        csv_file = f"./media/{pdf_file.split('.')[0]}.csv"
        try:
            with open(csv_file, 'w', newline='') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=["Type", "Key", "Value"])
                writer.writeheader()
                for data in result:
                    writer.writerow(data)
        except IOError:
            print("I/O error")

        files = ['result_lineitems.csv', f'{pdf_file.split(".")[0]}.csv']
        return files
    except:
        print("I/O error")
