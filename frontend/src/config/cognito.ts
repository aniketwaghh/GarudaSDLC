// Cognito OIDC Configuration
// Update these values with your AWS Cognito configuration
export const cognitoAuthConfig = {
  authority: "https://cognito-idp.us-west-2.amazonaws.com/us-west-2_gfX7i4kj2",
  client_id: "2pnlq64o6cv0ad6tfgasdktsa1",
  redirect_uri: "http://localhost:5173", // Update for production
  response_type: "code",
  scope: "phone openid email",
  post_logout_redirect_uri: "http://localhost:5173", // Update for production
};

// Cognito domain and logout configuration
export const cognitoDomain = "https://us-west-2gfx7i4kj2.auth.us-west-2.amazoncognito.com";
export const logoutUri = "http://localhost:5173"; // Update for production
