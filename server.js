const express = require('express');
const cors = require('cors');
const pkg = require('pg');
const dotenv = require('dotenv');

dotenv.config();
const { Pool } = pkg;

const app = express();
app.use(cors());
app.use(express.json());

// Default pool using environment variables
const defaultPool = new Pool({
  host: process.env.DB_HOST || 'localhost',
  port: process.env.DB_PORT || 5432,
  user: process.env.DB_USER || 'postgres',
  password: process.env.DB_PASSWORD || 'Tri@2004',
  database: process.env.DB_DATABASE || 'demand_forecast',
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
      FROM information_schema.columns 
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
  try {
    const { product, stockStatus, value } = req.body;
    console.log('Received feedback:', req.body);    
    // Here you would typically store the feedback in a database
    // For this example, we'll just log it and return a success response
    res.json({
      success: true,
      message: 'Feedback received successfully',
      feedback: { product, stockStatus, value }
    });
  } catch (err) {
    console.error('Feedback submission error:', err.message);
    res.status(500).json({
      success: false,
      error: 'Internal server error'
    });
  }
});