CREATE TABLE Sales (
    SaleID INT ,     
    CustomerID INT NOT NULL,                  
    ProductID INT NOT NULL,                   
    Quantity INT NOT NULL,                    
    SaleAmount DECIMAL(10, 2) NOT NULL,       
    SaleDate DATE NOT NULL,                   
    PaymentMethod VARCHAR(50),                
    SalesPersonID INT,                        
    Discount DECIMAL(5, 2),      
    TaxAmount DECIMAL(10, 2) ,    
    CreatedAt DATETIME2(6) ,     
    UpdatedAt DATETIME2(6) 
);