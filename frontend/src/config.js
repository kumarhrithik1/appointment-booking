// Central API configuration.
//
// Development (default):
//   BASE_URL = '' (empty string)
//   CRA's proxy in package.json forwards /api/* → http://localhost:8000
//   No changes needed here for local development.
//
// Production:
//   Create a .env file in the frontend folder and set:
//   REACT_APP_API_URL=https://your-production-domain.com
//   Then rebuild: npm run build

var config = {
  BASE_URL: process.env.REACT_APP_API_URL || 'http://127.0.0.1:8000',
};

export default config;