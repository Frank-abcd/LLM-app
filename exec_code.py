def exec_code(code: str):
    if 'python' in code.split('\n')[0]:
        code = '\n'.join(code.split('\n')[1:-1])
    
    try:
        namespace = {} 
        exec(code, namespace)
        result = namespace.get('result', None)
        if result is not None:
            return str(result)
        else:
            return "Code executed successfully but no result returned."
    except Exception as e:
        return "执行失败，原因：%s" % str(e)