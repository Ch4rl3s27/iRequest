-- SQL script to drop unused student views from the database
-- These views are no longer created by the application and can be safely removed

-- Drop BEED views
DROP VIEW IF EXISTS BEED_Students_all;
DROP VIEW IF EXISTS BEED_Students_firstyear;
DROP VIEW IF EXISTS BEED_Students_secondyear;
DROP VIEW IF EXISTS BEED_Students_thirdyear;
DROP VIEW IF EXISTS BEED_Students_fourthyear;

-- Drop BSED views
DROP VIEW IF EXISTS BSED_Students_all;
DROP VIEW IF EXISTS BSED_Students_firstyear;
DROP VIEW IF EXISTS BSED_Students_secondyear;
DROP VIEW IF EXISTS BSED_Students_thirdyear;
DROP VIEW IF EXISTS BSED_Students_fourthyear;

-- Drop CS views
DROP VIEW IF EXISTS CS_Students_all;
DROP VIEW IF EXISTS CS_Students_firstyear;
DROP VIEW IF EXISTS CS_Students_secondyear;
DROP VIEW IF EXISTS CS_Students_thirdyear;
DROP VIEW IF EXISTS CS_Students_fourthyear;

-- Drop HM views
DROP VIEW IF EXISTS HM_Students_all;
DROP VIEW IF EXISTS HM_Students_firstyear;
DROP VIEW IF EXISTS HM_Students_secondyear;
DROP VIEW IF EXISTS HM_Students_thirdyear;
DROP VIEW IF EXISTS HM_Students_fourthyear;

