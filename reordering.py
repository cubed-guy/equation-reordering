from abc import ABC

def print_return(f):
	def inner(*args, **kwargs):
		# print('running', f.__qualname__, 'on', *args)
		r = f(*args, **kwargs)
		# print(f.__qualname__, 'returned', r)
		return r
	return inner

class Expression(ABC):
	def __repr__(self):
		return f'{self.__class__.__name__}({", ".join(map(repr, self.__dict__.values()))})'

	def __str__(self):
		return f'{self.__class__.__name__}({", ".join(map(str, self.__dict__.values()))})'

	def __eq__(self, other):
		return self.__class__ == other.__class__ and self.__dict__ == other.__dict__

	def __neg__(self):
		return Neg(self)

	def __add__(self, other):
		return Sum(self, other)

	def __sub__(self, other):
		return Sum(self, Neg(other))

	def __mul__(self, other):
		return Product(self, other)

	def __truediv__(self, other):
		return Product(self, Inv(other))

	def __pow__(self, other):
		return Exp(self, other)

	def factor(self, fac_exp):
		return self

	def distribute(self):
		return self

class Sum(Expression):
	def __init__(self, *exps):
		super().__init__()
		self.exps = exps

	def __str__(self):
		return ' + '.join(f'({exp})' if isinstance(exp, Sum) else f'{exp}' for exp in self.exps)

	@print_return
	def extract(self, rhs, index):
		return self.exps[index], Sum(rhs, Neg(Sum(*self.exps[:index], *self.exps[index+1:])))

	@print_return
	def simplify(self):
		exps = [exp.simplify() for exp in self.exps if exp != Var('0')]

		sums = (sub_exp for exp in exps if isinstance(exp, Sum) for sub_exp in exp.exps)
		not_sums = (exp for exp in exps if not isinstance(exp, Sum))

		exps = (*sums, *not_sums)

		if not exps: return Var('0')

		if len(exps) == 1: return exps[0]

		return Sum(*exps)

	def factor(self, fac_exp):
		fac_exps = []
		for sum_exp in self.exps:
			if isinstance(sum_exp, Neg):
				sum_exp = sum_exp.exp
				neg = True
			else:
				neg = False

			if isinstance(sum_exp, Product):
				i = sum_exp.exps.index(fac_exp)
				_, exp = sum_exp.extract(Var('1'), i)
				out_exp = Inv(exp)

			elif fac_exp != sum_exp:
				raise ValueError('Could not factorise')
			else:
				out_exp = Var('1')

			if neg: fac_exps.append(Neg(out_exp))
			else: fac_exps.append(out_exp)

		return Sum(*fac_exps) * fac_exp

class Neg(Expression):
	def __init__(self, exp):
		super().__init__()
		self.exp = exp

	def __str__(self):
		if isinstance(self.exp, Sum):
			return f'-({self.exp!s})'
		return f'-{self.exp!s}'

	@print_return
	def extract(self, rhs, index = 0):
		if index != 0: raise IndexError('Neg only takes index 0')
		return self.exp, Neg(rhs)

	@print_return
	def simplify(self):

		exp = self.exp.simplify()
		if isinstance(exp, Neg): return exp.exp
		if isinstance(exp, Sum):
			return Sum(*(Neg(exp) for exp in exp.exps)).simplify()

		return Neg(exp)

class Product(Expression):
	def __init__(self, *exps):
		super().__init__()
		self.exps = exps
	
	def __str__(self):
		return ' '.join(f'({exp})' if isinstance(exp, (Sum, Neg)) else f'{exp}' for exp in self.exps)

	@print_return
	def extract(self, rhs, index):
		return self.exps[index], Product(rhs, Inv(self.__class__(*self.exps[:index], *self.exps[index+1:])))


	@print_return
	def simplify(self):
		exps = [exp.simplify() for exp in self.exps if exp != Var('1')]

		products = (sub_exp for exp in exps if isinstance(exp, Product) for sub_exp in exp.exps)
		not_products = (exp for exp in exps if not isinstance(exp, Product))

		exps = [*products, *not_products]

		if not exps: return Var('1')

		if len(exps) == 1: return exps[0]

		if Var('0') in exps: return Var('0')

		neg = False

		for i, exp in enumerate(exps):
			if isinstance(exp, Neg):
				exps[i] = exp.exp
				neg = not neg

		if neg: return Neg(Product(*exps).simplify())
		return Product(*exps)

	def distribute(self):
		for i, exp in enumerate(self.exps):
			if isinstance(exp, Sum): break
		else:
			raise ValueError('A Sum type is required to be able to distribute')

		# exp and i are not defined if self.exps is empty

		sum_exp, rem = self.extract(Var('1'), i)
		rem = Inv(rem)
		exps = (Product(rem, term) for term in sum_exp.exps)

		return Sum(*exps)

class Inv(Expression):
	def __init__(self, exp):
		super().__init__()
		self.exp = exp

	@print_return
	def extract(self, rhs, index = 0):
		if index != 0: raise IndexError('Inv only takes index 0')
		return self.exp, Inv(rhs)

	@print_return
	def simplify(self):
		exp = self.exp.simplify()
		if isinstance(exp, Inv): return exp.exp
		if isinstance(exp, Product):
			return Product(*(Inv(exp) for exp in exp.exps)).simplify()

		return Inv(exp)

class Exp(Expression):
	def __init__(self, base, exp):
		super().__init__()
		self.base = base
		self.exp = exp

	def __str__(self):
		if isinstance(self.base, (Sum, Neg, Product)):
			base = f'({self.base})'
		else: base = f'{self.base}'

		if isinstance(self.exp, (Sum, Neg, Product)):
			exp = f'({self.exp})'
		else: exp = f'{self.exp}'

		return f'{base}^{exp}'
	
	@print_return
	def extract(self, rhs, index = 1):
		if index == 0:
			return self.base, Exp(rhs, Inv(self.exp))
		if index == 1:
			return self.exp, Log(self.base, rhs)
		raise IndexError('Exp has only two valid indices: 0 and 1')

	@print_return
	def simplify(self):
		exp = self.exp.simplify()
		base = self.base.simplify()

		if isinstance(base, Exp):
			return Exp(base.base, Product((base.exp, exp)))

		return Exp(base, exp)

class Log(Expression):
	def __init__(self, base, arg):
		super().__init__()
		self.base = base
		self.arg = arg
	
	@print_return
	def extract(self, rhs, index = 1):
		if index == 0:
			return self.base, Exp(self.arg, Inv(rhs))
		if index == 1:
			return self.arg, Exp(self.base, rhs)
		raise IndexError('Log has only two valid indices: 0 and 1')

	@print_return
	def simplify(self):

		base = self.base.simplify()
		arg = self.arg.simplify()

		if isinstance(arg, Exp):
			return Product(arg.exp, Log(base, arg.base))

		if isinstance(base, Exp):
			return Product(Log(base.base, arg), Inv(base.exp))

		return Log(base, arg)

class Var(Expression):
	def __init__(self, name):
		self.name = name
	
	def __str__(self):
		return self.name

	@print_return
	def extract(self, rhs, index = 0):
		if index != 0: raise IndexError('Variables only take index 0')
		return self, rhs

	@print_return
	def simplify(self):
		return self

class Fn(Expression):
	def __init__(self, name, inv_name, arg):
		self.name = name
		self.inv_name = inv_name
		self.arg = arg

	def __str__(self):
		return f'{self.name}({self.arg})'
		
	def extract(self, rhs, index = 0):
		if index != 0: raise IndexError(f'{name!r} only takes index 0')
		return self.arg, Fn(self.inv_name, self.name, rhs)

	def simplify(self):
		if isinstance(self.arg, Fn) and self.arg.inv_name == self.name and self.inv_name == self.arg.name:
			return self.arg.arg

		return self

if __name__ == '__main__':
	stack = []
	while 1:
		print()

		for i, exp in enumerate(stack):
			print(f'[{len(stack) - i:3}]  ', exp)

		command = ''
		while not command:
			command = input(': ').strip()

		try:
			if   command == '+': r = stack.pop(); stack.append(stack.pop() + r)
			elif command == '-': r = stack.pop(); stack.append(stack.pop() - r)
			elif command == '*': r = stack.pop(); stack.append(stack.pop() * r)
			elif command == '/': r = stack.pop(); stack.append(stack.pop() / r)
			elif command == '^': r = stack.pop(); stack.append(stack.pop() ** r)

			elif command == '_': stack.append(Neg(stack.pop()))
			elif command == '.': stack.append(stack.pop().simplify())
			elif command == ',': stack.append(stack.pop().distribute().simplify())
			elif command.startswith(','):
				exp = stack.pop()
				if not isinstance(exp, Sum): raise TypeError('Can only factorise Sum types')
				sub_exp = exp.exps[0]
				if isinstance(sub_exp, Product):
					fac_exp = sub_exp.exps[int(command[1:])]
					stack.append(exp.factor(fac_exp).simplify())
				elif isinstance(sub_exp, Neg):
					stack.append(exp.factor(sub_exp.exp).simplify())
				else:
					stack.append(exp.factor(sub_exp).simplify())

			elif command == '$': stack.append(stack[-1])
			elif command.startswith('$'): stack.append(stack[-int(command[1:])])

			elif command.startswith('!'):
				stack.append(Fn(*command[1:].split(), stack.pop()))

			elif command == '/q':
				break
			elif command == '/d':
				stack.pop()
			elif command == '/s':
				stack.extend((stack.pop(), stack.pop()))

			elif command.startswith('\\'):
				stack.extend((stack.pop().extract(stack.pop(), int(command[1:])))[::-1])
			else:
				stack.append(Var(command))
		except Exception as e:
			print(f'Could not execute ({e.__class__.__name__})')
			print(e)
