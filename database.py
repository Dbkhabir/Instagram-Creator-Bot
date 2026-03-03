"""
Database management with SQLAlchemy
সব account data এখানে সেভ হবে
"""

from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config import config

Base = declarative_base()


class Account(Base):
    """Instagram account model"""
    __tablename__ = 'accounts'
    
    id = Column(Integer, primary_key=True)
    telegram_user_id = Column(String(50), nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=False)
    password = Column(String(100), nullable=False)
    email = Column(String(150), nullable=False)
    email_provider = Column(String(50), nullable=False)
    
    # 2FA Information
    two_fa_secret = Column(String(100))
    backup_codes = Column(Text)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    last_login = Column(DateTime)
    
    # Creation details
    creation_ip = Column(String(50))
    user_agent = Column(String(500))
    
    def __repr__(self):
        return f"<Account(username='{self.username}', email='{self.email}')>"


class CreationLog(Base):
    """Log all creation attempts - সব attempt এর লগ"""
    __tablename__ = 'creation_logs'
    
    id = Column(Integer, primary_key=True)
    telegram_user_id = Column(String(50), nullable=False, index=True)
    status = Column(String(20))  # success, failed, pending
    error_message = Column(Text)
    email_provider = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)
    duration_seconds = Column(Integer)
    
    def __repr__(self):
        return f"<CreationLog(status='{self.status}', provider='{self.email_provider}')>"


class EmailProviderStats(Base):
    """Track email provider reliability - কোন provider কতটা ভালো কাজ করছে"""
    __tablename__ = 'email_provider_stats'
    
    id = Column(Integer, primary_key=True)
    provider_name = Column(String(50), unique=True, nullable=False)
    total_attempts = Column(Integer, default=0)
    successful_attempts = Column(Integer, default=0)
    failed_attempts = Column(Integer, default=0)
    avg_response_time = Column(Integer)  # milliseconds
    last_used = Column(DateTime)
    is_working = Column(Boolean, default=True)
    
    @property
    def success_rate(self):
        if self.total_attempts == 0:
            return 0
        return (self.successful_attempts / self.total_attempts) * 100
    
    def __repr__(self):
        return f"<EmailProviderStats(provider='{self.provider_name}', success_rate={self.success_rate:.1f}%)>"


class Database:
    """Database manager class"""
    
    def __init__(self):
        self.engine = create_engine(config.DATABASE_URL)
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
    
    def add_account(self, telegram_user_id, username, password, email, email_provider,
                   two_fa_secret=None, backup_codes=None):
        """Add new account to database"""
        account = Account(
            telegram_user_id=telegram_user_id,
            username=username,
            password=password,
            email=email,
            email_provider=email_provider,
            two_fa_secret=two_fa_secret,
            backup_codes=backup_codes
        )
        self.session.add(account)
        self.session.commit()
        return account
    
    def get_user_accounts(self, telegram_user_id):
        """Get all accounts for a user"""
        return self.session.query(Account).filter_by(
            telegram_user_id=telegram_user_id,
            is_active=True
        ).all()
    
    def count_user_accounts(self, telegram_user_id):
        """Count user's active accounts"""
        return self.session.query(Account).filter_by(
            telegram_user_id=telegram_user_id,
            is_active=True
        ).count()
    
    def log_creation_attempt(self, telegram_user_id, status, email_provider,
                            error_message=None, duration_seconds=None):
        """Log creation attempt"""
        log = CreationLog(
            telegram_user_id=telegram_user_id,
            status=status,
            email_provider=email_provider,
            error_message=error_message,
            duration_seconds=duration_seconds
        )
        self.session.add(log)
        self.session.commit()
        return log
    
    def update_provider_stats(self, provider_name, success, response_time_ms):
        """Update email provider statistics"""
        stats = self.session.query(EmailProviderStats).filter_by(
            provider_name=provider_name
        ).first()
        
        if not stats:
            stats = EmailProviderStats(provider_name=provider_name)
            self.session.add(stats)
        
        stats.total_attempts += 1
        if success:
            stats.successful_attempts += 1
        else:
            stats.failed_attempts += 1
        
        # Update average response time
        if stats.avg_response_time:
            stats.avg_response_time = (stats.avg_response_time + response_time_ms) // 2
        else:
            stats.avg_response_time = response_time_ms
        
        stats.last_used = datetime.utcnow()
        stats.is_working = success or stats.success_rate > 50
        
        self.session.commit()
        return stats
    
    def get_best_email_provider(self):
        """Get most reliable email provider - সবচেয়ে ভালো provider খুঁজে বের করা"""
        providers = self.session.query(EmailProviderStats).filter_by(
            is_working=True
        ).order_by(
            EmailProviderStats.successful_attempts.desc()
        ).all()
        
        if providers:
            return providers[0].provider_name
        return None
    
    def close(self):
        """Close database connection"""
        self.session.close()


# Initialize database
db = Database()