"""
Example demonstrating WikiverseAuth for Wikidata authentication.

This example shows:
1. How to authenticate to Wikidata using bot passwords
2. How to make authenticated API requests
3. How to handle different Wikimedia instances
"""

from gkc import WikiverseAuth, AuthenticationError


def example_basic_auth():
    """Basic authentication example using environment variables."""
    print("=" * 60)
    print("Example 1: Basic Authentication")
    print("=" * 60)
    
    # Credentials should be set in environment variables:
    # export WIKIVERSE_USERNAME="YourUsername@YourBot"
    # export WIKIVERSE_PASSWORD="your_bot_password"
    
    try:
        auth = WikiverseAuth()
        
        if not auth.is_authenticated():
            print("Error: No credentials found in environment variables.")
            print("Please set WIKIVERSE_USERNAME and WIKIVERSE_PASSWORD")
            return
        
        print(f"Authenticating to: {auth.api_url}")
        print(f"Username: {auth.username}")
        print(f"Account: {auth.get_account_name()}")
        print(f"Bot: {auth.get_bot_name()}")
        
        # Login to the API
        auth.login()
        print("✓ Successfully logged in!")
        
        # Make an authenticated query
        response = auth.session.get(auth.api_url, params={
            "action": "query",
            "meta": "userinfo",
            "uiprop": "rights|groups",
            "format": "json"
        })
        
        user_info = response.json()
        if "query" in user_info and "userinfo" in user_info["query"]:
            user = user_info["query"]["userinfo"]
            print(f"\nUser Info:")
            print(f"  Name: {user.get('name')}")
            print(f"  Groups: {', '.join(user.get('groups', []))}")
            print(f"  Rights: {len(user.get('rights', []))} permissions")
        
        # Logout when done
        auth.logout()
        print("\n✓ Logged out successfully")
        
    except AuthenticationError as e:
        print(f"Authentication error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")


def example_custom_instance():
    """Example using a custom MediaWiki instance."""
    print("\n" + "=" * 60)
    print("Example 2: Custom MediaWiki Instance")
    print("=" * 60)
    
    # For custom instances, you might set:
    # export WIKIVERSE_API_URL="https://wiki.mycompany.com/w/api.php"
    
    # Or specify directly in code
    auth = WikiverseAuth(
        username="TestUser@TestBot",  # Replace with your credentials
        password="fake_password_for_example",
        api_url="https://custom.wiki.org/w/api.php"
    )
    
    print(f"API URL: {auth.api_url}")
    print(f"Username: {auth.username}")


def example_different_wikimedia_projects():
    """Example showing how to target different Wikimedia projects."""
    print("\n" + "=" * 60)
    print("Example 3: Different Wikimedia Projects")
    print("=" * 60)
    
    projects = {
        "Wikidata": "wikidata",
        "Wikipedia": "wikipedia",
        "Wikimedia Commons": "commons"
    }
    
    for name, api_shortcut in projects.items():
        auth = WikiverseAuth(
            username="User@Bot",  # Replace with your credentials
            password="fake_password",
            api_url=api_shortcut
        )
        print(f"{name:20s} -> {auth.api_url}")


def example_csrf_token():
    """Example getting CSRF token for edits."""
    print("\n" + "=" * 60)
    print("Example 4: Getting CSRF Token for Edits")
    print("=" * 60)
    
    try:
        auth = WikiverseAuth()
        
        if not auth.is_authenticated():
            print("No credentials found. Skipping example.")
            return
        
        auth.login()
        print("✓ Logged in")
        
        # Get CSRF token (required for most write operations)
        csrf_token = auth.get_csrf_token()
        print(f"CSRF Token: {csrf_token[:20]}...")
        
        print("\nYou can now use this token for edits, for example:")
        print("""
        edit_params = {
            "action": "edit",
            "title": "Test Page",
            "text": "Test content",
            "token": csrf_token,
            "format": "json"
        }
        response = auth.session.post(auth.api_url, data=edit_params)
        """)
        
        auth.logout()
        print("\n✓ Logged out")
        
    except AuthenticationError as e:
        print(f"Authentication error: {e}")


if __name__ == "__main__":
    print("\nWikiverseAuth Examples")
    print("=" * 60)
    print("Make sure to set up bot passwords first:")
    print("https://www.wikidata.org/wiki/Special:BotPasswords")
    print()
    
    # Run examples
    example_basic_auth()
    example_custom_instance()
    example_different_wikimedia_projects()
    example_csrf_token()
    
    print("\n" + "=" * 60)
    print("Examples complete!")
    print("=" * 60)
