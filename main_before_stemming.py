import os
import string
import math
import tkinter as tk


documents_folder = "documents"


# Words that are not useful for search
stop_words = {
    "the",
    "a",
    "an",
    "is",
    "are",
    "and",
    "or",
    "of",
    "in",
    "on",
    "to",
    "for",
    "with",
    "that",
    "this",
    "it",
    "its",
    "as",
    "by"
}


def build_index():
    inverted_index = {}
    word_frequencies = {}
    document_frequency = {}

    files = os.listdir(documents_folder)

    for file in files:
        print(f"Reading: {file}")

        with open(
            os.path.join(documents_folder, file),
            "r",
            encoding="utf-8"
        ) as document:

            text = document.read()
            words = text.split()

            words_in_document = set()

            for word in words:
                word = normalize_word(word)

                if not word:
                    continue

                if word in stop_words:
                    continue

                # Inverted index
                if word not in inverted_index:
                    inverted_index[word] = []

                if file not in inverted_index[word]:
                    inverted_index[word].append(file)

                # Word frequency
                if word not in word_frequencies:
                    word_frequencies[word] = {}

                if file not in word_frequencies[word]:
                    word_frequencies[word][file] = 0

                word_frequencies[word][file] += 1

                words_in_document.add(word)

            # Document Frequency
            for word in words_in_document:
                if word not in document_frequency:
                    document_frequency[word] = 0

                document_frequency[word] += 1

    return inverted_index, word_frequencies, document_frequency


def calculate_idf(document_frequency, total_documents):
    idf = {}

    for word, df in document_frequency.items():
        idf[word] = math.log(total_documents / df)

    return idf


def normalize_word(word):
    word = word.lower()
    word = word.strip(string.punctuation)

    if word.endswith("ies") and len(word) > 4:
        word = word[:-3] + "y"

    elif word.endswith("ing") and len(word) > 5:
        word = word[:-3]

    elif word.endswith("ed") and len(word) > 4:
        word = word[:-2]

    elif word.endswith("es") and len(word) > 4:
        word = word[:-2]

    elif word.endswith("s") and len(word) > 3:
        word = word[:-1]

    return word


def clean_query(query):
    words = query.lower().split()

    cleaned_words = []

    for word in words:
        word = normalize_word(word)

        if word and word not in stop_words:
            cleaned_words.append(word)

    return cleaned_words


def search_documents(query, inverted_index):
    query_words = clean_query(query)

    found_documents = set()

    # Find documents containing at least one query word
    for word in query_words:

        if word in inverted_index:

            for file in inverted_index[word]:
                found_documents.add(file)

    return found_documents, query_words


def rank_results(
    found_documents,
    query_words,
    word_frequencies,
    idf
):
    results = []

    for file in found_documents:

        score = 0
        matched_words = 0

        for word in query_words:

            if word in word_frequencies:

                if file in word_frequencies[word]:

                    frequency = word_frequencies[word][file]

                    word_idf = idf.get(word, 0)

                    # TF-IDF contribution
                    tfidf = frequency * word_idf

                    # If IDF is zero, use frequency
                    if tfidf == 0:
                        tfidf = frequency

                    score += tfidf
                    matched_words += 1

        results.append(
            (
                file,
                score,
                matched_words
            )
        )

    # First: higher score
    # Second: more matched query words
    results.sort(
        key=lambda x: (x[1], x[2]),
        reverse=True
    )

    return results


def get_snippet(file, query_words):

    with open(
        os.path.join(documents_folder, file),
        "r",
        encoding="utf-8"
    ) as document:

        text = document.read()

    text_lower = text.lower()

    for word in query_words:

        position = text_lower.find(word)

        if position != -1:

            start = max(0, position - 50)
            end = min(len(text), position + 150)

            snippet = text[start:end].replace("\n", " ")

            return "..." + snippet + "..."

    return "No matching text found."


# ---------------------------------------
# Build search engine
# ---------------------------------------

inverted_index, word_frequencies, document_frequency = build_index()

total_documents = len(os.listdir(documents_folder))

idf = calculate_idf(
    document_frequency,
    total_documents
)


# ---------------------------------------
# Search
# ---------------------------------------

def perform_search():

    query = search_entry.get().strip()

    results_text.delete("1.0", tk.END)

    if not query:

        results_text.insert(
            tk.END,
            "Please enter a search query."
        )

        return

    found_documents, query_words = search_documents(
        query,
        inverted_index
    )

    if not found_documents:

        results_text.insert(
            tk.END,
            "No documents found."
        )

        return

    results = rank_results(
        found_documents,
        query_words,
        word_frequencies,
        idf
    )

    results_text.insert(
        tk.END,
        f"Found {len(results)} document(s)\n\n"
    )

    for position, (
        file,
        score,
        matched_words
    ) in enumerate(results, start=1):

        results_text.insert(
            tk.END,
            f"{position}. {file} — Score: {score:.3f}\n"
        )

        results_text.insert(
            tk.END,
            f"   Matched query words: "
            f"{matched_words}/{len(query_words)}\n"
        )

        snippet = get_snippet(
            file,
            query_words
        )

        results_text.insert(
            tk.END,
            f"   {snippet}\n\n"
        )


# ---------------------------------------
# Create window
# ---------------------------------------

window = tk.Tk()

window.title(
    "International Relations Search Engine"
)

window.geometry(
    "800x600"
)


# Title
title_label = tk.Label(
    window,
    text="International Relations Search Engine",
    font=("Arial", 20)
)

title_label.pack(
    pady=20
)


# Search input
search_entry = tk.Entry(
    window,
    width=60,
    font=("Arial", 14)
)

search_entry.pack(
    pady=10
)


# Search with Enter
search_entry.bind(
    "<Return>",
    lambda event: perform_search()
)


# Search button
search_button = tk.Button(
    window,
    text="Search",
    font=("Arial", 12),
    command=perform_search
)

search_button.pack(
    pady=10
)


# Results
results_text = tk.Text(
    window,
    width=90,
    height=25,
    font=("Arial", 11)
)

results_text.pack(
    pady=20
)


# Start application
window.mainloop()