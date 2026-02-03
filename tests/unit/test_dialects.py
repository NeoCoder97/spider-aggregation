"""Tests for database dialect system."""

import pytest

from spider_aggregation.config import DatabaseConfig
from spider_aggregation.storage.dialects import (
    BaseDialect,
    MySQLDialect,
    PostgreSQLDialect,
    SQLiteDialect,
    get_dialect,
    get_supported_dialects,
    register_dialect,
)


class CustomDialect(BaseDialect):
    """Custom test dialect."""

    @property
    def name(self) -> str:
        return "custom"

    def build_url(self, config: DatabaseConfig) -> str:
        return "custom://test"

    def get_engine_kwargs(self, config: DatabaseConfig) -> dict:
        return {}

    def get_pool_class(self):
        return None


class TestDialectRegistry:
    """Tests for dialect registry."""

    def test_get_supported_dialects(self):
        """Test getting supported dialect list."""
        dialects = get_supported_dialects()
        assert "sqlite" in dialects
        assert "postgresql" in dialects
        assert "postgres" in dialects  # Alias
        assert "mysql" in dialects

    def test_get_sqlite_dialect(self):
        """Test getting SQLite dialect."""
        dialect = get_dialect("sqlite")
        assert isinstance(dialect, SQLiteDialect)
        assert dialect.name == "sqlite"

    def test_get_postgresql_dialect(self):
        """Test getting PostgreSQL dialect."""
        dialect = get_dialect("postgresql")
        assert isinstance(dialect, PostgreSQLDialect)
        assert dialect.name == "postgresql"

    def test_get_postgres_alias(self):
        """Test 'postgres' alias for 'postgresql'."""
        dialect = get_dialect("postgres")
        assert isinstance(dialect, PostgreSQLDialect)
        assert dialect.name == "postgresql"

    def test_get_mysql_dialect(self):
        """Test getting MySQL dialect."""
        dialect = get_dialect("mysql")
        assert isinstance(dialect, MySQLDialect)
        assert dialect.name == "mysql"

    def test_invalid_dialect(self):
        """Test invalid dialect raises error."""
        with pytest.raises(ValueError, match="Unsupported database dialect"):
            get_dialect("oracle")

    def test_register_custom_dialect(self):
        """Test registering custom dialect."""
        register_dialect("custom", CustomDialect)
        dialect = get_dialect("custom")
        assert isinstance(dialect, CustomDialect)
        assert dialect.name == "custom"


class TestSQLiteDialect:
    """Tests for SQLite dialect."""

    def test_build_url_from_path(self):
        """Test building URL from path."""
        dialect = SQLiteDialect()
        config = DatabaseConfig(path="data/test.db")
        url = dialect.build_url(config)
        assert url == "sqlite:///data/test.db"

    def test_build_url_from_url(self):
        """Test building URL from existing URL."""
        dialect = SQLiteDialect()
        config = DatabaseConfig(path="sqlite:////absolute/path.db")
        url = dialect.build_url(config)
        assert url == "sqlite:////absolute/path.db"

    def test_get_engine_kwargs(self):
        """Test engine kwargs."""
        dialect = SQLiteDialect()
        config = DatabaseConfig(path="data/test.db", echo=True)
        kwargs = dialect.get_engine_kwargs(config)

        assert kwargs["echo"] is True
        assert "connect_args" in kwargs
        assert kwargs["connect_args"]["check_same_thread"] is False
        assert kwargs["connect_args"]["timeout"] == 30
        assert "poolclass" in kwargs
        assert kwargs["pool_size"] == 5
        assert kwargs["max_overflow"] == 10

    def test_migration_kwargs(self):
        """Test migration kwargs."""
        dialect = SQLiteDialect()
        kwargs = dialect.get_migration_kwargs()
        assert kwargs == {"render_as_batch": True}

    def test_validate_config_valid(self):
        """Test validation of valid config."""
        dialect = SQLiteDialect()
        config = DatabaseConfig(path="data/test.db")
        errors = dialect.validate_config(config)
        assert errors == []

    def test_supports_json(self):
        """Test JSON support."""
        dialect = SQLiteDialect()
        assert dialect.supports_json is True

    def test_supports_array(self):
        """Test ARRAY support."""
        dialect = SQLiteDialect()
        assert dialect.supports_array is False


class TestPostgreSQLDialect:
    """Tests for PostgreSQL dialect."""

    def test_build_url_basic(self):
        """Test building basic URL."""
        dialect = PostgreSQLDialect()
        config = DatabaseConfig(
            type="postgresql",
            host="localhost",
            port=5432,
            database="testdb",
            user="testuser",
            password="testpass",
        )
        url = dialect.build_url(config)
        # Default port (5432) is omitted
        assert url == "postgresql://testuser:testpass@localhost/testdb"

    def test_build_url_without_password(self):
        """Test building URL without password."""
        dialect = PostgreSQLDialect()
        config = DatabaseConfig(
            type="postgresql",
            host="localhost",
            database="testdb",
            user="testuser",
            password=None,
        )
        url = dialect.build_url(config)
        assert url == "postgresql://testuser@localhost/testdb"

    def test_build_url_with_ssl(self):
        """Test building URL with SSL mode."""
        dialect = PostgreSQLDialect()
        config = DatabaseConfig(
            type="postgresql",
            host="localhost",
            database="testdb",
            user="testuser",
            password="testpass",
            ssl_mode="require",
        )
        url = dialect.build_url(config)
        # Default port (5432) is omitted
        assert url == "postgresql://testuser:testpass@localhost/testdb?sslmode=require"

    def test_build_url_default_port(self):
        """Test building URL with default port omitted."""
        dialect = PostgreSQLDialect()
        config = DatabaseConfig(
            type="postgresql",
            host="localhost",
            port=5432,  # Default port - should be omitted
            database="testdb",
            user="testuser",
            password="testpass",
        )
        url = dialect.build_url(config)
        assert url == "postgresql://testuser:testpass@localhost/testdb"

    def test_get_engine_kwargs(self):
        """Test engine kwargs."""
        dialect = PostgreSQLDialect()
        config = DatabaseConfig(type="postgresql", echo=True)
        kwargs = dialect.get_engine_kwargs(config)

        assert kwargs["echo"] is True
        assert kwargs["pool_pre_ping"] is True
        assert "poolclass" in kwargs

    def test_migration_kwargs(self):
        """Test migration kwargs are empty."""
        dialect = PostgreSQLDialect()
        kwargs = dialect.get_migration_kwargs()
        assert kwargs == {}

    def test_validate_config_valid(self):
        """Test validation of valid config."""
        dialect = PostgreSQLDialect()
        config = DatabaseConfig(
            type="postgresql",
            host="localhost",
            database="testdb",
            user="testuser",
        )
        errors = dialect.validate_config(config)
        assert errors == []

    def test_validate_config_missing_database(self):
        """Test validation fails without database."""
        dialect = PostgreSQLDialect()
        config = DatabaseConfig(type="postgresql", host="localhost")
        errors = dialect.validate_config(config)
        assert any("database" in e.lower() for e in errors)

    def test_validate_config_invalid_ssl_mode(self):
        """Test validation fails with invalid SSL mode."""
        # Pydantic validates at model creation, not in dialect.validate_config
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            DatabaseConfig(
                type="postgresql",
                host="localhost",
                database="testdb",
                ssl_mode="invalid",
            )

    def test_supports_json(self):
        """Test JSON support."""
        dialect = PostgreSQLDialect()
        assert dialect.supports_json is True

    def test_supports_array(self):
        """Test ARRAY support."""
        dialect = PostgreSQLDialect()
        assert dialect.supports_array is True

    def test_requires_cascade_type(self):
        """Test CASCADE type requirement."""
        dialect = PostgreSQLDialect()
        assert dialect.requires_cascade_type is True


class TestMySQLDialect:
    """Tests for MySQL dialect."""

    def test_build_url_basic(self):
        """Test building basic URL."""
        dialect = MySQLDialect()
        config = DatabaseConfig(
            type="mysql",
            host="localhost",
            port=3306,
            database="testdb",
            user="testuser",
            password="testpass",
        )
        url = dialect.build_url(config)
        # Default port (3306) is omitted
        assert url == "mysql+pymysql://testuser:testpass@localhost/testdb?charset=utf8mb4"

    def test_build_url_without_password(self):
        """Test building URL without password."""
        dialect = MySQLDialect()
        config = DatabaseConfig(
            type="mysql",
            host="localhost",
            database="testdb",
            user="testuser",
            password=None,
        )
        url = dialect.build_url(config)
        # Default port (3306) is omitted
        assert url == "mysql+pymysql://testuser@localhost/testdb?charset=utf8mb4"

    def test_get_engine_kwargs(self):
        """Test engine kwargs."""
        dialect = MySQLDialect()
        config = DatabaseConfig(type="mysql", echo=True)
        kwargs = dialect.get_engine_kwargs(config)

        assert kwargs["echo"] is True
        assert kwargs["pool_pre_ping"] is True
        assert kwargs["pool_recycle"] == 3600
        assert "poolclass" in kwargs

    def test_migration_kwargs(self):
        """Test migration kwargs are empty."""
        dialect = MySQLDialect()
        kwargs = dialect.get_migration_kwargs()
        assert kwargs == {}

    def test_validate_config_valid(self):
        """Test validation of valid config."""
        dialect = MySQLDialect()
        config = DatabaseConfig(
            type="mysql",
            host="localhost",
            database="testdb",
            user="testuser",
        )
        errors = dialect.validate_config(config)
        assert errors == []

    def test_validate_config_missing_database(self):
        """Test validation fails without database."""
        dialect = MySQLDialect()
        config = DatabaseConfig(type="mysql", host="localhost")
        errors = dialect.validate_config(config)
        assert any("database" in e.lower() for e in errors)

    def test_supports_json(self):
        """Test JSON support."""
        dialect = MySQLDialect()
        assert dialect.supports_json is True

    def test_supports_array(self):
        """Test ARRAY support."""
        dialect = MySQLDialect()
        assert dialect.supports_array is False

    def test_requires_cascade_type(self):
        """Test CASCADE type requirement."""
        dialect = MySQLDialect()
        assert dialect.requires_cascade_type is False


class TestDatabaseConfig:
    """Tests for DatabaseConfig with dialect support."""

    def test_default_sqlite_type(self):
        """Test default type is sqlite."""
        config = DatabaseConfig()
        assert config.type == "sqlite"

    def test_type_normalization(self):
        """Test type normalization."""
        config = DatabaseConfig(type="PostgreSQL")
        assert config.type == "postgresql"

    def test_type_normalization_postgres_alias(self):
        """Test 'postgres' alias normalization."""
        config = DatabaseConfig(type="postgres")
        assert config.type == "postgresql"

    def test_invalid_type(self):
        """Test invalid type raises error."""
        with pytest.raises(ValueError, match="Invalid database type"):
            DatabaseConfig(type="oracle")

    def test_port_validation(self):
        """Test port validation."""
        with pytest.raises(ValueError, match="Port must be between"):
            DatabaseConfig(type="postgresql", port=99999)

    def test_valid_port(self):
        """Test valid port is accepted."""
        config = DatabaseConfig(type="postgresql", port=5432)
        assert config.port == 5432

    def test_ssl_mode_validation(self):
        """Test SSL mode validation."""
        with pytest.raises(ValueError, match="Invalid ssl_mode"):
            DatabaseConfig(type="postgresql", ssl_mode="invalid")

    def test_valid_ssl_mode(self):
        """Test valid SSL mode is accepted."""
        config = DatabaseConfig(type="postgresql", ssl_mode="require")
        assert config.ssl_mode == "require"
