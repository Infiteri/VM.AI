"""
pytest configuration for API tests.
"""
import pytest
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.core.database import Base, get_db


TEST_DB_URL = "sqlite:///./test_endpoints.db"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override database dependency for testing."""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """Create tables once for all tests."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db():
    """Provide a fresh DB session for each test."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.rollback()
        db.close()


@pytest.fixture(scope="function")
def client(db):
    """Provide FastAPI test client."""
    return TestClient(app)


@pytest.fixture(scope="session")
def log_base_dir():
    """Base directory for test logs."""
    log_dir = Path(__file__).parent / "logs"
    workflows_dir = log_dir / "workflows"
    api_dir = log_dir / "api"
    
    workflows_dir.mkdir(parents=True, exist_ok=True)
    api_dir.mkdir(parents=True, exist_ok=True)
    
    return str(log_dir)


@pytest.fixture(scope="function")
def clean_test_data(db):
    """Fixture to clean test data after each test."""
    yield
    from app.models import Task, TaskDraft, UnscheduledTask, TaskCategory
    
    db.query(UnscheduledTask).filter(
        UnscheduledTask.task_id.in_(
            db.query(Task.id).filter(Task.name.like('TEST_%'))
        )
    ).delete(synchronize_session=False)
    
    db.query(TaskCategory).filter(
        TaskCategory.task_id.in_(
            db.query(Task.id).filter(Task.name.like('TEST_%'))
        )
    ).delete(synchronize_session=False)
    
    db.query(Task).filter(Task.name.like('TEST_%')).delete(synchronize_session=False)
    db.query(TaskDraft).filter(TaskDraft.name.like('TEST_%')).delete(synchronize_session=False)
    
    db.commit()


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "order(n): run test in specified order")


def pytest_collection_modifyitems(items):
    """Auto-order tests based on filename."""
    def get_order(item):
        name = item.nodeid
        if "workflows" in name:
            if "wf_01" in name: return 1
            if "wf_02" in name: return 2
            if "wf_03" in name: return 3
            if "wf_04" in name: return 4
            if "wf_05" in name: return 5
            if "wf_06" in name: return 6
            if "wf_07" in name: return 7
            if "wf_08" in name: return 8
            if "wf_09" in name: return 9
            if "wf_10" in name: return 10
        elif "api_tests" in name:
            if "test_01" in name: return 11
            if "test_02" in name: return 12
            if "test_03" in name: return 13
            if "test_04" in name: return 14
            if "test_05" in name: return 15
            if "test_06" in name: return 16
            if "test_07" in name: return 17
            if "test_08" in name: return 18
            if "test_09" in name: return 19
            if "test_10" in name: return 20
            if "test_11" in name: return 21
            if "test_12" in name: return 22
            if "test_13" in name: return 23
        return 50
    
    items.sort(key=get_order)
