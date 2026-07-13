import py_vncorenlp

from configs.config import BASE_DIR
from src.data_models.dependency_token import DependencyToken, Sentence


class VnCoreNLPParser:

    _pipeline = None

    @classmethod
    def get_pipeline(cls):
        if cls._pipeline is None:
            cls._pipeline = py_vncorenlp.VnCoreNLP(
                save_dir=str(
                    BASE_DIR / "resources" / "third_party" / "vncorenlp"
                )
            )

        return cls._pipeline
    
    @classmethod
    def parse_file(cls, input_file, output_file):
        pipeline = cls.get_pipeline()
        return pipeline.annotate_file(input_file, output_file=output_file)

    @classmethod
    def parse_text(cls, text):
        pipeline = cls.get_pipeline()
        raw_output = pipeline.annotate_text(text)
        return cls._to_dependency_tokens(raw_output)
    
    @classmethod
    def _to_dependency_tokens(cls, raw_output):

        document = []

        for sentence_id, sentence in raw_output.items():
            tokens = []
            for token in sentence:
                tokens.append(
                    DependencyToken(
                        id=token["index"],
                        word=token["wordForm"],
                        pos=token["posTag"],
                        head=token["head"],
                        dep=token["depLabel"]
                    )
                )

            document.append(Sentence(id=sentence_id, tokens=tokens))

        return document
