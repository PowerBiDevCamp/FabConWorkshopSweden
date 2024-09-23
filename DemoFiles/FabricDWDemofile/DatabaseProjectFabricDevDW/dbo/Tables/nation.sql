CREATE TABLE dbo.nation
(
    NationID INT ,
    NationName VARCHAR(100) NOT NULL,      
    CountryCode CHAR(3) NOT NULL,             
    Region VARCHAR(50),                      
    Population BIGINT,                       
    GDP DECIMAL(18, 2),                       
    CreatedDate DATETIME2(6), 
    ModifiedDate DATETIME2(6) NULL   
);