-- Role for regular app operations (subject to RLS)
CREATE ROLE app_user WITH LOGIN PASSWORD 'app_password';
-- Role for migrations and global analytics (bypasses RLS)
CREATE ROLE app_admin WITH LOGIN PASSWORD 'admin_password';

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE aira TO app_admin;
ALTER DATABASE aira OWNER TO app_admin;