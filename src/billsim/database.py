#!/usr/bin/env python3

from billsim.constants import POSTGRES_PW
from sqlalchemy.orm import sessionmaker
from sqlmodel import create_engine

postgres_url = f"postgresql://postgres:{POSTGRES_PW}@localhost"

engine = create_engine(postgres_url, echo=False)

SessionLocal = sessionmaker(autocommit=False,
                            autoflush=False,
                            expire_on_commit=False,
                            bind=engine)
