import express from "express";
import cors from "cors";
import pkg from "pg";
import dotenv from "dotenv";
dotenv.config();
const { Pool } = pkg;

const app = express();
app.use(cors());
app.use(express.json());

// Default pool using environment variables
const defaultPool = new Pool({
  host: process.env.DB_HOST,
  port: process.env.DB_PORT ,
  user: process.env.DB_USERNAME ,
  password: process.env.DB_PASSWORD ,
  database: process.env.DB_DATABASE ,
  ssl: process.env.DB_SSL === 'true' // Optional SSL
});

// Function to create a pool with custom config
const createPool = (config) => {
  return new Pool({
    host: config.host,
    port: config.port,
    user: config.username,
    password: config.password,
    database: config.database,
    ssl: config.ssl || false
  });
};

// Test connection with custom config
app.post("/api/test-connection", async (req, res) => {
  let pool;
  try {
    const config = req.body;
    console.log('Testing connection with config:', {
      ...config,
      password: '***' // Don't log password
    });
    
    pool = createPool(config);
    const result = await pool.query("SELECT NOW() as current_time");
    console.log('Connection successful:', result.rows[0]);
    
    res.json({ 
      success: true, 
      message: 'Connection successful',
      serverTime: result.rows[0].current_time
    });
  } catch (err) {
    console.error('Connection error:', err.message);
    res.json({ 
      success: false, 
      error: err.message 
    });
  } finally {
    if (pool) {
      await pool.end();
    }
  }
});

// ERP data fetch with custom config
app.post("/api/erp-data", async (req, res) => {
  let pool;
  try {
    const { query, config } = req.body;
    console.log('Fetching ERP data with query:', query);
    console.log('Using config:', {
      ...config,
      password: 'Tri@2004' // Don't log password
    });
    
    // Use custom config if provided, otherwise use default
    pool = config ? createPool(config) : defaultPool;
    
    const result = await pool.query(query);
    console.log(`Query executed successfully. Rows returned: ${result.rows.length}`);
    
    // Log first few rows for debugging
    if (result.rows.length > 0) {
      console.log('Sample data:', result.rows.slice(0, 3));
    }
    
    res.json({ 
      success: true, 
      results: result.rows,
      rowCount: result.rows.length
    });
  } catch (err) {
    console.error('Query error:', err.message);
    res.json({ 
      success: false, 
      error: err.message,
      query: req.body.query
    });
  } finally {
    // Only end the pool if it's a custom one
    if (pool && req.body.config) {
      await pool.end();
    }
  }
});

// Health check endpoint
app.get("/api/health", (req, res) => {
  res.json({ 
    status: 'OK', 
    timestamp: new Date().toISOString(),
    server: 'ERP API Server'
  });
});

// Get database schema info
app.post("/api/schema", async (req, res) => {
  let pool;
  try {
    const config = req.body;
    pool = config ? createPool(config) : defaultPool;
    
    const result = await pool.query(`
      SELECT 
        table_name, 
        column_name, 
        data_type,
        is_nullable
      FROM demand_forecast.information_schema.columns
      WHERE table_schema = 'public'
      ORDER BY table_name, ordinal_position
    `);
    
    // Group by table
    const schema = {};
    result.rows.forEach(row => {
      if (!schema[row.table_name]) {
        schema[row.table_name] = [];
      }
      schema[row.table_name].push({
        column: row.column_name,
        type: row.data_type,
        nullable: row.is_nullable === 'YES'
      });
    });
    
    res.json({ 
      success: true, 
      schema: schema 
    });
  } catch (err) {
    console.error('Schema query error:', err.message);
    res.json({ 
      success: false, 
      error: err.message 
    });
  } finally {
    if (pool && req.body && Object.keys(req.body).length > 0) {
      await pool.end();
    }
  }
});

// Sample data endpoint for testing
app.post("/api/sample-data", async (req, res) => {
  let pool;
  try {
    const config = req.body;
    pool = config ? createPool(config) : defaultPool;
    
    const result = await pool.query(`
      SELECT 
        week,
        sku,
        dc,
        forecast_ai_qty,
        created_at,
        updated_at
      FROM demand_forecast 
      LIMIT 10
    `);
    
    res.json({ 
      success: true, 
      results: result.rows,
      message: 'Sample data retrieved successfully'
    });
  } catch (err) {
    console.error('Sample data error:', err.message);
    res.json({ 
      success: false, 
      error: err.message 
    });
  } finally {
    if (pool && req.body && Object.keys(req.body).length > 0) {
      await pool.end();
    }
  }
});

const PORT = process.env.PORT || 5000;

app.listen(PORT, () => {
  console.log(`ERP API Server running on port ${PORT}`);
  console.log('Environment variables:');
  console.log('- DB_HOST:', process.env.DB_HOST || 'localhost');
  console.log('- DB_PORT:', process.env.DB_PORT || 5432);
  console.log('- DB_DATABASE:', process.env.DB_DATABASE);
  console.log('- DB_USER:', process.env.DB_USER || 'postgres');
  console.log('- DB_PASSWORD:', process.env.DB_PASSWORD);
});


app.post("/api/feedback", async (req, res) => {
  const client = await defaultPool.connect();
  try {
    const {
      cheeseDemand,
      snacksDemand,
      bakeryDemand,
      beveragesDemand,
      frozenDemand,
      dc,
      product,
      stockStatus,
      value,
    } = req.body;

    console.log("📩 Received feedback:", req.body);

    let naive_forecast = 0;
    let sku = "";
    const week = Math.ceil(
      (((new Date() - new Date(new Date().getFullYear(), 0, 1)) /
        86400000) +
        new Date(new Date().getFullYear(), 0, 1).getDay() +
        1) /
        7
    );

    // Map product → sku & naive_forecast
    if (product === "Cheese") {
      naive_forecast = cheeseDemand;
      sku = "SKU003_Cheese";
    } else if (product === "Snacks") {
      naive_forecast = snacksDemand;
      sku = "SKU001_Snacks";
    } else if (product === "Bakery") {
      naive_forecast = bakeryDemand;
      sku = "SKU004_Bakery";
    } else if (product === "Beverages") {
      naive_forecast = beveragesDemand;
      sku = "SKU002_Beverages";
    } else if (product === "Frozen") {
      naive_forecast = frozenDemand;
      sku = "SKU005_Frozen";
    }
    naive_forecast = Number(naive_forecast) ;
    // Adjust forecast
    const numericValue = Number(value) || 0;
    const festival_adjusted_forecast =
      stockStatus === "Overstock"
        ? naive_forecast - numericValue
        : stockStatus === "Understock"
        ? naive_forecast + numericValue
        : naive_forecast;

    const actual = naive_forecast + numericValue;

    // Insert into PostgreSQL
    await client.query(
      `INSERT INTO baseline_forecast
      (week, sku, dc, naive_forecast, festival_adjusted_forecast, actual)
      VALUES ($1, $2, $3, $4, $5, $6)`,
      [week, sku, dc, naive_forecast, festival_adjusted_forecast, actual]
    );

    res.json({
      success: true,
      message: "Feedback saved to database",
      feedback: { week, sku, dc, naive_forecast, festival_adjusted_forecast, actual },
    });
  } catch (err) {
    console.error("❌ Feedback submission error:", err.message);
    res.status(500).json({ success: false, error: err.message });
  } finally {
    client.release();
  }
});


app.get("/api/export-baseline", async (req, res) => {
  const client = await defaultPool.connect();
  try {
    const result = await client.query("SELECT * FROM baseline_forecast");

    // Convert to CSV
    const headers = Object.keys(result.rows[0]).join(",") + "\n";
    const rows = result.rows
      .map((row) =>
        Object.values(row)
          .map((val) => `"${val}"`)
          .join(",")
      )
      .join("\n");

    const csvData = headers + rows;

    res.header("Content-Type", "text/csv");
    res.attachment("baseline_forecast_export.csv");
    res.send(csvData);
  } catch (err) {
    console.error("❌ CSV Export Error:", err.message);
    res.status(500).json({ success: false, error: err.message });
  } finally {
    client.release();
  }
});
