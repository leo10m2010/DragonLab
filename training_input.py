"""Expected input failures that recover without forgetting a reserved turn."""

class RecoverableInputError(RuntimeError):
    def __init__(self,message,*,method,code):
        if method not in ('drag','space'):raise ValueError('Método de carga inválido')
        super().__init__(message);self.method=method;self.code=code
