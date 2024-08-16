

class texthandler():
    def __call__(self, text):
        paragraphs = [para.strip() for para in text.split('\n\n') if para.strip()]
        html_output = ""
        for i, paragraph in enumerate(paragraphs, 1):
            html_output += f'<div id="paragraph-{i}">{paragraph}</div>\n'
        return text
