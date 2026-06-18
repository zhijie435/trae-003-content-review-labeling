from .database import Base, engine
from .models import Annotator, AnnotationTask, Annotation, Inspection, SamplingBatch


def init_db():
    Base.metadata.create_all(bind=engine)
