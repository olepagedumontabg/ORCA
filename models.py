from main import db
from sqlalchemy import Column, Integer, String, Text

class Product(db.Model):
    __tablename__ = 'products'
    
    id = Column(Integer, primary_key=True)
    sku = Column(String(50), unique=True, nullable=False, index=True)
    category = Column(String(50), nullable=False, index=True)
    brand = Column(String(50), nullable=True)
    family = Column(String(50), nullable=True)
    series = Column(String(50), nullable=True)
    nominal_dimensions = Column(String(50), nullable=True)
    installation = Column(String(50), nullable=True)
    max_door_width = Column(Integer, nullable=True)
    width = Column(Integer, nullable=True)
    length = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    product_data = Column(Text, nullable=True)  # JSON data for all other attributes
    
    def __repr__(self):
        return f'<Product {self.sku}>'


class Compatibility(db.Model):
    __tablename__ = 'compatibilities'
    
    id = Column(Integer, primary_key=True)
    source_sku = Column(String(50), nullable=False, index=True)
    target_sku = Column(String(50), nullable=False, index=True)
    target_category = Column(String(50), nullable=False, index=True)
    requires_return_panel = Column(String(50), nullable=True)  # SKU of required return panel if needed
    
    def __repr__(self):
        return f'<Compatibility {self.source_sku} -> {self.target_sku}>'