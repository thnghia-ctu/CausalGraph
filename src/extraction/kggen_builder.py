from pydoc import text

from kg_gen import KGGen

class KGGenBuilder:
    def __init__(self):
        self.kg_gen = KGGen(
            model="gemini/gemini-2.5-flash",  # Default model
            temperature=0.0,        # Default temperature
            api_key="AIzaSyALlQkQsONQ9dJLNYYSUnoniMNiDModhQY"  # Optional if set in environment or using a local model
        )

    def build_kg(self, text):
        kg = self.kg_gen.extract(text)
        return kg
    
    def test(self, text=None):
        if not text:
            text = "The cost of investment hinders the application of digital tools, while education level and technical training promote it. The application of digital tools increases rice productivity and production efficiency."
        kg = self.kg_gen.generate(input_data=text, cluster=True)
        KGGen.visualize(kg, "graph_kg.html", open_in_browser=True)