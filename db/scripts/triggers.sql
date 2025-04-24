-- Support function that will be called by the trigger trig_update_stock_last_data_point
CREATE OR REPLACE FUNCTION update_stock_last_data_point() 
RETURNS TRIGGER AS $$
BEGIN
    -- Update the last_data_point_date in the stocks table
    -- only if the new price_date is more recent than the current last_data_point_date
    UPDATE stocks
    SET last_data_point_date = NEW.price_date
    WHERE stock_id = NEW.stock_id
    AND (last_data_point_date IS NULL OR NEW.price_date > last_data_point_date);
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to update the last_data_point_date in the stocks table
-- whenever a new stock price is inserted or updated in the stock_price_historical table
CREATE TRIGGER trig_update_stock_last_data_point
AFTER INSERT OR UPDATE ON stock_price_historical
FOR EACH ROW
EXECUTE FUNCTION update_stock_last_data_point();