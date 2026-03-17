import json

def generate_org_and_faq(org_name, org_url, faqs=None, same_as=None, language='en'):
    graph = []
    org = {
        "@type": "Organization",
        "name": org_name,
        "url": org_url,
        "inLanguage": language,
        "sameAs": same_as or [],
        # provide alternateName for sites that have Arabic variations
        "alternateName": []
    }
    graph.append(org)

    if faqs:
        faq_page = {
            "@type": "FAQPage",
            "mainEntity": faqs
        }
        graph.append(faq_page)

    schema = {
        "@context": "https://schema.org",
        "@graph": graph
    }
    return json.dumps(schema, indent=2, ensure_ascii=False)


def generate_arabic_org_schema(org_name_en, org_name_ar, org_url, faqs=None, same_as=None):
    """Generate Organization + FAQ schema with Arabic `inLanguage` and alternateName."""
    graph = []
    org = {
        "@type": "Organization",
        "name": org_name_en,
        "alternateName": [org_name_ar],
        "url": org_url,
        "inLanguage": "ar",
        "sameAs": same_as or []
    }
    graph.append(org)

    if faqs:
        # ensure FAQPage uses inLanguage ar and contains Arabic Q/A
        faq_page = {
            "@type": "FAQPage",
            "inLanguage": "ar",
            "mainEntity": faqs
        }
        graph.append(faq_page)

    schema = {"@context": "https://schema.org", "@graph": graph}
    return json.dumps(schema, indent=2, ensure_ascii=False)

def make_question_answer(question, answer):
    return {
        "@type": "Question",
        "name": question,
        "acceptedAnswer": {
            "@type": "Answer",
            "text": answer
        }
    }
