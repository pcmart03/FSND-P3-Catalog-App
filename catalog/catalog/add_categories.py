from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Category

engine = create_engine('postgresql://catalog:catalog1@localhost/catalog')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()


categories = ['Hand Tools', 'Power Tools', 'Electrical', 'Plumbing', 'Lumber',
              'Safety']

for c in categories:
    new_category = Category(name=c)
    session.add(new_category)
    session.commit()


print "Categories added"
