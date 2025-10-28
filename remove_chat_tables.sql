-- Remove chat-related database tables
-- Run this script to clean up chat tables from your database

-- Drop chat-related tables in correct order (due to foreign key constraints)
DROP TABLE IF EXISTS message_status;
DROP TABLE IF EXISTS messages;
DROP TABLE IF EXISTS conversation_participants;
DROP TABLE IF EXISTS conversations;
DROP TABLE IF EXISTS users;

-- Note: The 'notifications' table is kept as it's used for general notifications
-- and not specifically for chat functionality
