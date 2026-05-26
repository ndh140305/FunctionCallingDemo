import math
import ast
from simpleeval import EvalWithCompoundTypes

def calculate_expression(expression: str) -> dict:
    """Tính toán một biểu thức toán học.
    Args:
        expression: Biểu thức toán học dạng chuỗi (ví dụ: "2 + 3 * 4", "sqrt(16)").
    Returns:
        dict chứa biểu thức gốc và kết quả tính toán.
    """

    # allowed_functions = {
    #     "sqrt": math.sqrt,
    #     "abs": abs,
    #     "pow": pow,
    #     "round": round,
    #     "sin": math.sin,
    #     "cos": math.cos,
    #     "tan": math.tan,
    #     "log": math.log,
    #     "log10": math.log10,
    #     "pi": math.pi,
    #     "e": math.e,
    # }
    blacklisted_names = {"comb", "perm", "modf", "frexp"}

    allowed_functions = {}
    for name in dir(math):
        if not name.startswith("_") and name not in blacklisted_names:
            allowed_functions[name] = getattr(math, name)

    allowed_functions.update({
        "abs": abs,
        "round": round,
        "pow": pow,
        "max": max,
        "min": min
    })

    s = EvalWithCompoundTypes(functions=allowed_functions, names=allowed_functions)

    s.nodes[ast.List] = s._eval_list    
    s.nodes[ast.Tuple] = s._eval_tuple  
    s.nodes[ast.Dict] = s._eval_dict    
    s.nodes[ast.Set] = s._eval_set

    try:
        result = s.eval(expression)
        return {
            "expression": expression,
            "result": result,
        }
    except Exception as e:
        return {"error": f"Không thể tính toán biểu thức: {str(e)}"}
        
math_tool_declaration = {
    "name": "calculate_expression",
    "description": "Tính toán một biểu thức toán học. Hỗ trợ các phép toán cơ bản và hàm toán học như sqrt, sin, cos, log.",
    "parameters": {
        "type": "object",
        "properties": {
            "expression": {
                "type": "string",
                "description": "Biểu thức toán học cần tính, ví dụ: '2 + 3 * 4', 'sqrt(16)', 'pow(2, 10)'",
            },
        },
        "required": ["expression"],
    },
}