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

	def eval_consts(self):
		return self

class Sum(Expression):
	def __init__(self, *exps):
		super().__init__()
		self.exps = exps

	def __str__(self):
		return ' + '.join(f'({exp})' if isinstance(exp, Sum) else f'{exp}' for exp in self.exps)

	@print_return
	def extract(self, rhs, index):
		if isinstance(index, slice):
			return Sum(*self.exps[index]), Sum(rhs, Neg(Sum(*self.exps[:index.start or 0], *self.exps[index.stop:])))
		if isinstance(index, int):
			return self.exps[index], Sum(rhs, Neg(Sum(*self.exps[:index], *self.exps[index+1:])))
		print(index, 'is not an int or a slice')
		raise TypeError(f'{index!r} is not an int or a slice')

	@print_return
	def select(self, name, index):
		if isinstance(index, slice):
			return Sum(*self.exps[index]), Sum(*self.exps[:index.start or 0], Var(name), *self.exps[index.stop:])
		if isinstance(index, int):
			return self.exps[index], Sum(*self.exps[:index], Var(name), *self.exps[index+1:])
		print(index, 'is not an int or a slice')
		raise TypeError(f'{index!r} is not an int or a slice')

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
				# print('finding', fac_exp, 'in', sum_exp)
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

	@print_return
	def substitute(self, find_exp, sub_exp):
		return Sum(*(sub_exp if exp == find_exp else exp.substitute(find_exp, sub_exp) for exp in self.exps))

	@print_return
	def eval_consts(self):
		exps = [exp.eval_consts() for exp in self.exps]
		const = 0
		out_exps = []
		for exp in exps:
			if isinstance(exp, Var) and exp.is_const():
				const += float(exp.name)
			else:
				out_exps.append(exp)

		if not out_exps:
			return Var(str(const))
		return Sum(Var(str(const)), *out_exps)

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
	def select(self, name, index = 0):
		if index != 0: raise IndexError('Neg only takes index 0')
		return self.exp, Neg(Var(name))

	@print_return
	def simplify(self):

		exp = self.exp.simplify()
		if isinstance(exp, Neg): return exp.exp
		if isinstance(exp, Sum):
			return Sum(*(Neg(exp) for exp in exp.exps)).simplify()

		return Neg(exp)

	def distribute(self):
		return Neg(self.exp.distribute())

	@print_return
	def substitute(self, find_exp, sub_exp):
		if self.exp == find_exp: return Neg(sub_exp)
		return Neg(self.exp.substitute(find_exp, sub_exp))

	@print_return
	def eval_consts(self):
		post_const = self.exp.eval_consts()
		if isinstance(post_const, Var) and post_const.is_const():
			return Var(str(-float(post_const.name)))

		return post_const


class Product(Expression):
	def __init__(self, *exps):
		super().__init__()
		self.exps = exps
	
	def __str__(self):
		return ' '.join(f'({exp})' if isinstance(exp, (Product, Sum, Neg)) else f'{exp}' for exp in self.exps)

	@print_return
	def extract(self, rhs, index):
		return self.exps[index], Product(rhs, Inv(Product(*self.exps[:index], *self.exps[index+1:])))

	@print_return
	def select(self, name, index):
		if isinstance(index, slice):
			return Product(*self.exps[index]), Product(*self.exps[:index.start or 0], Var(name), *self.exps[index.stop:])
		if isinstance(index, int):
			return self.exps[index], Product(*self.exps[:index], Var(name), *self.exps[index+1:])
		print(index, 'is not an int or a slice')
		raise TypeError(f'{index!r} is not an int or a slice')

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

	@print_return
	def substitute(self, find_exp, sub_exp):
		return Product(*(sub_exp if exp == find_exp else exp.substitute(find_exp, sub_exp) for exp in self.exps))

	def eval_consts(self):
		exps = [exp.eval_consts() for exp in self.exps]
		const = 1
		out_exps = []
		for exp in exps:
			if isinstance(exp, Var) and exp.name.replace('.', '', 1).isdigit():
				const *= float(exp.name)
			else:
				out_exps.append(exp)

		if not out_exps:
			return Var(str(const))
		return Product(Var(str(const)), *out_exps)


class Inv(Expression):  # Inverse
	def __init__(self, exp):
		super().__init__()
		self.exp = exp

	@print_return
	def extract(self, rhs, index = 0):
		if index != 0: raise IndexError('Inv only takes index 0')
		return self.exp, Inv(rhs)

	@print_return
	def select(self, name, index = 0):
		if index != 0: raise IndexError('Inv only takes index 0')
		return self.exp, Inv(Var(name))

	@print_return
	def simplify(self):
		exp = self.exp.simplify()
		if isinstance(exp, Inv): return exp.exp
		if isinstance(exp, Neg): return Neg(Inv(exp.exp).simplify())
		if isinstance(exp, Product):
			return Product(*(Inv(exp) for exp in exp.exps)).simplify()

		return Inv(exp)


	@print_return
	def substitute(self, find_exp, sub_exp):
		if self.exp == find_exp: return Inv(sub_exp)
		return Inv(self.exp.substitute(find_exp, sub_exp))

	@print_return
	def eval_consts(self):
		post_const = self.exp.eval_consts()
		if isinstance(post_const, Var) and post_const.is_const():
			return Var(str(1/float(post_const.name)))

		return post_const

class Exp(Expression):  # Exponent
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
	def extract(self, rhs, index = 1):
		if index == 0:
			return self.base, Exp(Var(name), self.exp)
		if index == 1:
			return self.exp, Exp(self.base, Var(name))
		raise IndexError('Exp has only two valid indices: 0 and 1')

	@print_return
	def simplify(self):
		exp = self.exp.simplify()
		base = self.base.simplify()

		if isinstance(base, Exp):
			return Exp(base.base, Product((base.exp, exp)))

		return Exp(base, exp)

	@print_return
	def substitute(self, find_exp, sub_exp):
		if self.base == find_exp: base = sub_exp
		else: base = self.base.substitute(find_exp, sub_exp)

		if self.exp == find_exp: exp = sub_exp
		else: exp = self.exp.substitute(find_exp, sub_exp)

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
	def select(self, name, index = 1):
		if index == 0:
			return self.base, Log(Var(name), self.arg)
		if index == 1:
			return self.arg, Log(self.base, Var(name))
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

	@print_return
	def substitute(self, find_exp, sub_exp):
		if self.arg == find_exp: arg = sub_exp
		else: arg = self.arg.substitute(find_exp, sub_exp)

		if self.base == find_exp: base = sub_exp
		else: base = self.base.substitute(find_exp, sub_exp)

		return Log(arg, base)


class Var(Expression):
	def __init__(self, name):
		self.name = name
	
	def __str__(self):
		return self.name

	def is_const(self):
		if self.name.startswith('-'):
			name = self.name[1:]
		else:
			name = self.name
		return name.replace('.', '', 1).isdigit()

	@print_return
	def extract(self, rhs, index = 0):
		if index != 0: raise IndexError('Variables only take index 0')
		return self, rhs

	@print_return
	def select(self, name, index = 0):
		if index != 0: raise IndexError('Variables only take index 0')
		return self, Var(name)

	@print_return
	def simplify(self):
		return self

	@print_return
	def substitute(self, find_exp, sub_exp):
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


	@print_return
	def substitute(self, find_exp, sub_exp):
		if self.arg == find_exp: arg = sub_exp
		else: arg = self.arg.substitute(find_exp, sub_exp)

		return Fn(self.name, self.inv_name, arg)

if __name__ == '__main__':
	stack = [Var('0')]
	while 1:
		print()

		for i, exp in enumerate(stack[1:], 1):
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
			elif command.startswith('.'):
				split = command[1:].split()

				if len(split) == 2:  # select index
					print('select')
					index, name = split
					index = int(index)
					stack.extend(stack.pop().select(name, index)[::-1])
				elif len(split) == 3:  # select slice
					print('select slice')
					start, stop, name = split
					start = int(start)
					stop = int(stop)
					stack.extend(stack.pop().select(name, slice(start, stop))[::-1])
				else:
					raise ValueError('Invalid Command Format. Expected exactly 2 or 3 arguments')

			elif command == ',': stack.append(stack.pop().distribute().simplify())
			elif command.startswith(','):
				exp = stack.pop()
				if isinstance(exp, Neg):
					neg = True
					exp = exp.exp
				else:
					neg = False

				if not isinstance(exp, Sum): raise TypeError('Can only factorise Sum types')
				term = exp.exps[0]

				if isinstance(term, Neg): term = term.exp

				index = int(command[1:])

				if isinstance(term, Product):
					fac_exp = term.exps[index]
				elif index != 0:
					raise IndexError('Prime term can only be indexed with 0')
				else:
					fac_exp = term

				if neg:
					stack.append(Neg(exp.factor(fac_exp)).simplify())
				else:
					stack.append(exp.factor(fac_exp).simplify())

			elif command == '$': stack.append(stack[-1])
			elif command.startswith('$'): stack.append(stack[-int(command[1:])])

			elif command.startswith('!'):
				stack.append(Fn(*command[1:].split(), stack.pop()))

			elif command == '/q':
				break

			elif command == '\\':
				stack.pop()

			elif command == '/r':
				print(repr(stack[-1]))
			elif command == '/l':
				print()
				exp = stack[-1]
				if isinstance(exp, (Neg, Inv)):
					print(exp.__class__.__name__, end = ' ')
					exp = exp.exp

				print(exp.__class__.__name__)
				for i, term in enumerate(exp.exps):
					print(f'({i:2}) ', term)

			elif command == '/ll':
				exp = stack[-1]
				if isinstance(exp, (Neg, Inv)):
					print(exp.__class__.__name__, end = ' ')
					exp = exp.exp

				print(exp.__class__.__name__)
				exp = exp.exps[0]

				if isinstance(exp, (Neg, Inv)):
					print(exp.__class__.__name__, end = ' ')
					exp = exp.exp

				print(exp.__class__.__name__)
				for i, term in enumerate(exp.exps):
					print(f'({i:2}) ', term)

			elif command.startswith('/s'):
				split = command[2:].split()
				if len(split) == 0:  # swap
					print('swap')
					stack.append(stack.pop(-2))
				elif len(split) == 1:  # substitute
					print('sub')
					name = split[0]
					sub_exp = stack.pop()
					exp = stack.pop()
					stack.extend([exp.substitute(Var(name), sub_exp), sub_exp])
				else:
					raise ValueError('Invalid Command Format. Expected at most 1 argument')

			elif command == '=':
				stack.append(stack.pop().eval_consts())

			elif command.startswith('='):
				index = command[1:]
				if ' ' not in index: index = int(index)
				else:
					start, stop = index.split()
					# print(start, stop)
					index = slice(int(start), int(stop))

				print(index)

				stack.extend((stack.pop().extract(stack.pop(), index))[::-1])

			else:
				stack.append(Var(command))
		except Exception as e:
			print(f'Could not execute ({e.__class__.__name__})')
			print(e)

		if not stack or stack[0] != Var('0'):
			stack.insert(0, Var('0'))
