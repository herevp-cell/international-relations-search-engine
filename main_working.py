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


# --------------------------------------------------
# BUILD SEARCH INDEX
# --------------------------------------------------

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

            for word in words:

                word = word.lower()
                word = word.strip(string.punctuation)

                if not word:
                    continue

                if word in stop_words:
                    continue

                # Inverted index
                if word not in inverted_index:
                    inverted_index[word] = []

                if file not in inverted_index[word]:

                    inverted_index[word].append(file)

                    # Document frequency
                    if word not in document_frequency:
                        document_frequency[word] = 0

                    document_frequency[word] += 1

                # Word frequency
                if word not in word_frequencies:
                    word_frequencies[word] = {}

                if file not in word_frequencies[word]:
                    word_frequencies[word][file] = 0

                word_frequencies[word][file] += 1

    return (
        inverted_index,
        word_frequencies,
        document_frequency
    )


# --------------------------------------------------
# CALCULATE IDF
# --------------------------------------------------

def calculate_idf(document_frequency, total_documents):

    idf = {}

    for word, df in document_frequency.items():

        idf[word] = math.log(
            total_documents / df
        )

    return idf


# --------------------------------------------------
# SEARCH
# --------------------------------------------------

def search_documents(query, inverted_index):

    query = query.lower()

    query_words = query.split()

    # Clean query
    cleaned_words = []

    for word in query_words:

        word = word.strip(string.punctuation)

        if word and word not in stop_words:
            cleaned_words.append(word)

    query_words = cleaned_words

    found_documents = None

    for word in query_words:

        if word in inverted_index:

            documents = set(
                inverted_index[word]
            )

            if found_documents is None:

                found_documents = documents

            else:

                found_documents = (
                    found_documents.intersection(documents)
                )

        else:

            found_documents = set()

            break

    if found_documents is None:
        found_documents = set()

    return found_documents, query_words


# --------------------------------------------------
# RANK RESULTS USING TF-IDF
# --------------------------------------------------

def rank_results(
    found_documents,
    query_words,
    word_frequencies,
    idf
):

    results = []

    for file in found_documents:

        score = 0

        for word in query_words:

            if word in word_frequencies:

                if file in word_frequencies[word]:

                    # TF
                    tf = word_frequencies[word][file]

                    # IDF
                    word_idf = idf.get(word, 0)

                    # TF-IDF
                    score += tf * word_idf

        results.append(
            (file, score)
        )

    # Highest score first
    results.sort(
        key=lambda x: x[1],
        reverse=True
    )

    return results


# --------------------------------------------------
# GET TEXT SNIPPET
# --------------------------------------------------

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

            start = max(
                0,
                position - 50
            )

            end = min(
                len(text),
                position + 150
            )

            snippet = text[
                start:end
            ].replace(
                "\n",
                " "
            )

            return "..." + snippet + "..."

    return "No matching text found."


# --------------------------------------------------
# BUILD INDEX
# --------------------------------------------------

inverted_index, word_frequencies, document_frequency = build_index()

total_documents = len(
    os.listdir(documents_folder)
)

idf = calculate_idf(
    document_frequency,
    total_documents
)


# --------------------------------------------------
# TEST IDF
# --------------------------------------------------

print()
print("Document Frequency:")

print(
    "international:",
    document_frequency.get(
        "international",
        0
    )
)

print(
    "france:",
    document_frequency.get(
        "france",
        0
    )
)

print(
    "european:",
    document_frequency.get(
        "european",
        0
    )
)

print(
    "law:",
    document_frequency.get(
        "law",
        0
    )
)

print()
print("IDF:")

print(
    "international:",
    idf.get(
        "international",
        0
    )
)

print(
    "france:",
    idf.get(
        "france",
        0
    )
)

print(
    "european:",
    idf.get(
        "european",
        0
    )
)

print(
    "law:",
    idf.get(
        "law",
        0
    )
)


# --------------------------------------------------
# SEARCH BUTTON FUNCTION
# --------------------------------------------------

def perform_search():

    query = search_entry.get().strip()

    # Clear previous results
    results_text.delete(
        "1.0",
        tk.END
    )

    # Empty search
    if not query:

        results_text.insert(
            tk.END,
            "Please enter a search query."
        )

        return

    # Search
    found_documents, query_words = search_documents(
        query,
        inverted_index
    )

    # Results found
    if found_documents:

        results = rank_results(
            found_documents,
            query_words,
            word_frequencies,
            idf
        )

        for position, (file, score) in enumerate(
            results,
            start=1
        ):

            results_text.insert(
                tk.END,
                f"{position}. {file} — TF-IDF: {score:.3f}\n"
            )

            snippet = get_snippet(
                file,
                query_words
            )

            results_text.insert(
                tk.END,
                f"   {snippet}\n\n"
            )

    # Nothing found
    else:

        results_text.insert(
            tk.END,
            "No documents found."
        )


# --------------------------------------------------
# CREATE WINDOW
# --------------------------------------------------

window = tk.Tk()

window.title(
    "International Relations Search Engine"
)

window.geometry(
    "800x600"
)


# --------------------------------------------------
# TITLE
# --------------------------------------------------

title_label = tk.Label(
    window,
    text="International Relations Search Engine",
    font=("Arial", 20)
)

title_label.pack(
    pady=20
)


# --------------------------------------------------
# SEARCH INPUT
# --------------------------------------------------

search_entry = tk.Entry(
    window,
    width=60,
    font=("Arial", 14)
)

search_entry.pack(
    pady=10
)


# Press Enter to search
search_entry.bind(
    "<Return>",
    lambda event: perform_search()
)


# --------------------------------------------------
# SEARCH BUTTON
# --------------------------------------------------

search_button = tk.Button(
    window,
    text="Search",
    font=("Arial", 12),
    command=perform_search
)

search_button.pack(
    pady=10
)


# --------------------------------------------------
# RESULTS
# --------------------------------------------------

results_text = tk.Text(
    window,
    width=90,
    height=25,
    font=("Arial", 11)
)

results_text.pack(
    pady=20
)


# --------------------------------------------------
# START APPLICATION
# --------------------------------------------------

window.mainloop()