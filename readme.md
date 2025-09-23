# DutyChart Project

## Overview
DutyChart is a web application designed to manage and streamline duty scheduling and administrative tasks. This project includes a frontend interface, backend API, Django admin panel, and Swagger API documentation for easy integration and management.

## Deployment Details

### SuperUser Credentials
The following credentials are for administrative access to the system:

- **Email**: admin-dutychart@ntc.net.np
- **Username**: dutychartadmin
- **Employee ID**: 7816
- **Full Name**: Buddhi Krishna Thapa
- **Password**: pass123pass

> **Note**: Ensure these credentials are kept secure and only shared with authorized personnel.

### Access URLs
The application can be accessed at the following endpoints:

- **Frontend Access**: [http://10.26.204.149](http://10.26.204.149)
- **Backend Access**: [http://10.26.204.149:8000](http://10.26.204.149:8000)
- **Django Admin Access**: [http://10.26.204.149/admin/](http://10.26.204.149/admin/)
- **Swagger API Documentation**: [http://10.26.204.149/swagger/](http://10.26.204.149/swagger/)

### Usage Notes
- Use the provided SuperUser credentials to log in to the Django Admin panel for administrative tasks.
- The Swagger API documentation provides detailed information about available API endpoints and their usage.
- Ensure you are on the correct network to access the IP-based URLs listed above.

## Setup Instructions
1. Clone the repository:
   ```bash
   git clone <repository-url>
   ```
2. Navigate to the project directory:
   ```bash
   cd dutychart
   ```
3. Follow additional setup instructions (e.g., installing dependencies, configuring environment variables) as outlined in the project documentation.

## Security Considerations
- Change the default SuperUser password immediately after deployment.
- Restrict access to the IP addresses listed above to authorized users only.
- Regularly update dependencies and monitor the application for security vulnerabilities.

## Contributing
Contributions are welcome! Please follow these steps:
1. Fork the repository.
2. Create a new branch (`git checkout -b feature/your-feature`).
3. Commit your changes (`git commit -m 'Add your feature'`).
4. Push to the branch (`git push origin feature/your-feature`).
5. Open a Pull Request.

## License
This project is licensed under the [MIT License](LICENSE).
