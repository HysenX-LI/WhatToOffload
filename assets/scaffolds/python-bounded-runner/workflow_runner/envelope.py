def envelope(status, summary, *, result=None, required_action=None, diagnostics=None, resume=None):
    return {
        "status": status,
        "summary": summary,
        "result": result,
        "required_action": required_action,
        "diagnostics": diagnostics,
        "resume": resume,
    }
