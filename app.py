# [Previous imports remain the same]

@app.route('/sso/acs', methods=['POST'])
def acs():
    req = prepare_flask_request(request)
    auth = init_saml_auth(req)
    
    logger.info("Processing SAML response")
    auth.process_response()
    errors = auth.get_errors()
    
    if errors:
        logger.error(f"SAML Authentication errors: {errors}")
        logger.error(f"Last error reason: {auth.get_last_error_reason()}")
        return f'Authentication failed: {", ".join(errors)}', 401
    
    if not auth.is_authenticated():
        logger.error("SAML Authentication failed: User not authenticated")
        return 'Authentication failed: Not authenticated', 401

    # Get user attributes
    attributes = auth.get_attributes()
    name_id = auth.get_nameid()
    logger.info(f"User authenticated. NameID: {name_id}")
    logger.info(f"User attributes: {attributes}")

    # Store user information in session
    session['samlUserdata'] = attributes
    session['samlNameId'] = name_id
    session['user'] = {
        'preferred_username': name_id,
        'name': attributes.get('displayName', [name_id])[0] if attributes else name_id
    }

    # Redirect to the next URL or admin page
    if 'next_url' in session:
        next_url = session.pop('next_url')
        logger.info(f"Redirecting to: {next_url}")
        return redirect(next_url)
    return redirect(url_for('admin'))

# [Rest of the file remains the same]