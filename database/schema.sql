-- Main table for customer information
CREATE TABLE Customers (
    customer_id SERIAL PRIMARY KEY,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100),
    phone_number VARCHAR(20) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE,
    address TEXT,
    customer_type VARCHAR(50) DEFAULT 'Prospect', -- e.g., Prospect, Hot Lead, VIP Client
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Table for dealership staff (users of the system)
CREATE TABLE Users (
    user_id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL, -- Store hashed passwords, never plaintext
    full_name VARCHAR(150),
    role VARCHAR(50) NOT NULL, -- e.g., Sales Executive, Sales Manager, Admin
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Table for vehicle inventory and models
CREATE TABLE Vehicles (
    vehicle_id SERIAL PRIMARY KEY,
    model_name VARCHAR(255) NOT NULL,
    brand VARCHAR(100),
    base_price NUMERIC(15, 2) NOT NULL,
    configuration_details JSONB, -- For storing custom configurations
    stock_status VARCHAR(50) DEFAULT 'Available'
);

-- Central table to log all interactions (calls, emails, meetings)
CREATE TABLE Interactions (
    interaction_id SERIAL PRIMARY KEY,
    customer_id INTEGER REFERENCES Customers(customer_id) ON DELETE SET NULL,
    user_id INTEGER REFERENCES Users(user_id) ON DELETE SET NULL,
    channel VARCHAR(50) NOT NULL, -- e.g., Phone, Email, WhatsApp, In-Person
    content TEXT, -- Transcript, email body, or meeting notes
    summary TEXT,
    outcome VARCHAR(255), -- e.g., Test drive scheduled, Quote sent
    interaction_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Table to store generated documents like invoices and quotes
CREATE TABLE Documents (
    document_id SERIAL PRIMARY KEY,
    customer_id INTEGER REFERENCES Customers(customer_id) ON DELETE CASCADE,
    document_type VARCHAR(50) NOT NULL, -- e.g., Invoice, Quotation, Proforma
    document_data JSONB, -- Stores all data used to generate the document
    file_path VARCHAR(255) NOT NULL, -- Local path to the generated PDF
    status VARCHAR(50) DEFAULT 'Draft',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by_user_id INTEGER REFERENCES Users(user_id)
);

-- Table for scheduling test drives and showroom visits
CREATE TABLE Appointments (
    appointment_id SERIAL PRIMARY KEY,
    customer_id INTEGER REFERENCES Customers(customer_id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES Users(user_id) ON DELETE SET NULL, -- Assigned sales exec
    vehicle_id INTEGER REFERENCES Vehicles(vehicle_id),
    appointment_time TIMESTAMP WITH TIME ZONE NOT NULL,
    status VARCHAR(50) DEFAULT 'Scheduled', -- e.g., Scheduled, Completed, Canceled
    notes TEXT
);

-- Table to track the final sale of a vehicle
CREATE TABLE Sales (
    sale_id SERIAL PRIMARY KEY,
    customer_id INTEGER REFERENCES Customers(customer_id) ON DELETE RESTRICT,
    vehicle_id INTEGER REFERENCES Vehicles(vehicle_id) ON DELETE RESTRICT,
    final_price NUMERIC(15, 2) NOT NULL,
    sale_date DATE NOT NULL,
    document_id INTEGER REFERENCES Documents(document_id), -- Link to the final invoice
    sold_by_user_id INTEGER REFERENCES Users(user_id)
);

-- Table for agent-created or user-assigned tasks
CREATE TABLE Tasks (
    task_id SERIAL PRIMARY KEY,
    assigned_to_user_id INTEGER REFERENCES Users(user_id),
    customer_id INTEGER REFERENCES Customers(customer_id),
    description TEXT NOT NULL,
    due_date DATE,
    status VARCHAR(50) DEFAULT 'Pending', -- e.g., Pending, In Progress, Complete
    priority VARCHAR(20) DEFAULT 'Normal'
);

-- Specific log for voice agent interactions
CREATE TABLE Call_Logs (
    call_log_id SERIAL PRIMARY KEY,
    interaction_id INTEGER REFERENCES Interactions(interaction_id) ON DELETE CASCADE,
    call_sid VARCHAR(255), -- ID from voice provider (Vapi/AI Sensy)
    duration_seconds INTEGER,
    recording_path VARCHAR(255), -- Local path to the recording
    call_status VARCHAR(50) -- e.g., Completed, No Answer, Failed
);

-- Table to register and manage the different AI agents
CREATE TABLE Agents (
    agent_id SERIAL PRIMARY KEY,
    agent_name VARCHAR(100) UNIQUE NOT NULL, -- e.g., Voice Agent, Document Agent
    agent_type VARCHAR(50),
    status VARCHAR(50) DEFAULT 'Active',
    last_health_check TIMESTAMP WITH TIME ZONE
);

