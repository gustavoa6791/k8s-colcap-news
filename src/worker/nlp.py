"""
Módulo de procesamiento de lenguaje natural (NLP).
Análisis de sentimiento usando pysentimiento (español).
"""
from src.common.config import Config
from pysentimiento import create_analyzer


class SentimentAnalyzer:

    def __init__(self):
        self.economic_keywords = Config.ECONOMIC_KEYWORDS
        self.analyzer = create_analyzer(task="sentiment", lang="es")

    def analyze(self, text):
        """
        Sentimiento del texto usando pysentimiento.
        Modelo entrenado en español.
        """
        try:
            # Limitar texto 
            text_truncated = text[:512] if len(text) > 512 else text

            result = self.analyzer.predict(text_truncated)

            # Mapear resultado de pysentimiento al formato esperado
            label = result.output  # 'POS', 'NEG', 'NEU'
            probas = result.probas  # {'POS': 0.8, 'NEG': 0.1, 'NEU': 0.1}

            # Calcular polaridad (-1 a 1)
            polarity = probas.get('POS', 0) - probas.get('NEG', 0)

            # Mapear clasificación
            classification_map = {
                'POS': 'positivo',
                'NEG': 'negativo',
                'NEU': 'neutral'
            }
            classification = classification_map.get(label, 'neutral')

            # Confianza es la probabilidad del label predicho
            confidence = probas.get(label, 0)

            return {
                'polarity': round(polarity, 3),
                'subjectivity': round(1 - probas.get('NEU', 0), 3),
                'classification': classification,
                'confidence': round(confidence, 3)
            }
        except Exception as e:
            print(f"[NLP] Error en análisis: {e}")
            return {
                'polarity': 0,
                'subjectivity': 0,
                'classification': 'neutral',
                'confidence': 0
            }

    def detect_economic_keywords(self, text):
        """
        Palabras claves en el texto
        """
        try:
            text_lower = text.lower()
            found_keywords = []

            for keyword in self.economic_keywords:
                if keyword in text_lower:
                    count = text_lower.count(keyword)
                    found_keywords.append({'keyword': keyword, 'count': count})

            relevance_score = min(
                100,
                len(found_keywords) * 10 + sum(k['count'] for k in found_keywords) * 2
            )

            return {
                'keywords': found_keywords[:10],
                'total_keywords': len(found_keywords),
                'relevance_score': relevance_score
            }
        except:
            return {'keywords': [], 'total_keywords': 0, 'relevance_score': 0}
