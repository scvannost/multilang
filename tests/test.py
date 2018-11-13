import numpy as np
from multilang import as_multilang, Master
import unittest


class Test_Multilang_Func(unittest.TestCase):
	def test_start(self):
		with self.subTest('start in R'):
			ry = as_multilang('''#! multilang R
				a <- 3
			''')
			self.assertIn('a', ry.who_r)
			d = ry.dump_r()
			self.assertIn('a', d)
			self.assertEqual(d['a'], 3)
			del d

		with self.subTest('start in Mat'):
			ry = as_multilang('''#! multilang mat
				a = 3''')
			self.assertIn('a', ry.who_mat)
			d = ry.dump_mat()
			self.assertIn('a', d)
			self.assertEqual(d['a'], 3)
			del d

		with self.subTest('start py'):
			ry = as_multilang(
'''#! multilang py
a = 3''')
			self.assertIn('a', ry.who_py)
			d = ry.dump_py()
			self.assertIn('a',d)
			self.assertEqual(d['a'], 3)
			del d

		with self.subTest('start implied py'):
			ry = as_multilang(
'''#! multilang
a = 3''')
			self.assertIn('a', ry.who_py)
			d = ry.dump_py()
			self.assertIn('a', d)
			self.assertEqual(d['a'], 3)
			del d

	def test_r(self):
		with self.subTest('r_to_py'):
			ry = as_multilang(
'''#! multilang R
a <- 3
#! python -> a
a *= 2''')
			self.assertIn('a', ry.who_py)
			self.assertIn('a', ry.who_r)
			p = ry.dump_py()
			r = ry.dump_r()
			self.assertIn('a', p)
			self.assertIn('a', r)
			self.assertEqual(p['a'], 6)
			self.assertEqual(r['a'], 3)
			del p,r

		with self.subTest('r_to_mat'):
			ry = as_multilang(
'''#! multilang R
a <-3
#! matlab -> a
a = a+1''')
			self.assertIn('a', ry.who_mat)
			self.assertIn('a', ry.who_r)
			m = ry.dump_mat()
			r = ry.dump_r()
			self.assertIn('a', m)
			self.assertIn('a', r)
			self.assertEqual(m['a'], 4)
			self.assertEqual(r['a'], 3)
			del m,r

		with self.subTest('py_to_r'):
			ry = as_multilang(
'''#! multilang
a = 3
#! r -> a
a = 7''')
			self.assertIn('a', ry.who_py)
			self.assertIn('a', ry.who_r)
			p = ry.dump_py()
			r = ry.dump_r()
			self.assertIn('a', p)
			self.assertIn('a', r)
			self.assertEqual(p['a'], 3)
			self.assertEqual(r['a'], 7)
			del p,r



class Test_Multilang_Master_Base(unittest.TestCase):
	def test_r_only(self):
		ry = Master(mat=False)
		self.assertTrue(ry.isalive_r)
		self.assertFalse(ry.isalive_mat)

	def test_mat_only(self):
		ry = Master(r=False)
		self.assertTrue(ry.isalive_mat)
		self.assertFalse(ry.isalive_r)

	def test_connect(self):
		with self.subTest('nothing'):
			ry = Master(r=False, mat=False)
			self.assertFalse(ry.isalive_r)
			self.assertFalse(ry.isalive_mat)

		with self.subTest('R only'):
			ry.connect(mat=False)
			self.assertTrue(ry.isalive_r)
			self.assertFalse(ry.isalive_mat)

		with self.subTest('both'):
			ry.connect()
			self.assertTrue(ry.isalive_r)
			self.assertTrue(ry.isalive_mat)

	def test_reconnect(self):
		ry = Master(r=False, mat=False)
		with self.subTest('mat only, no force'):
			self.assertIsNone(ry.mat_object._mat_object)
			ry.reconnect(r=False, force=False)
			self.assertTrue(ry.isalive_mat)
			self.assertFalse(ry.isalive_r)
			self.assertIsNotNone(ry.mat_object._mat_object)

		with self.subTest('R only, force'):
			self.assertIsNone(ry.r_object._r_object)
			ry.reconnect(mat=False)
			self.assertTrue(ry.isalive_mat)
			self.assertTrue(ry.isalive_r)
			self.assertIsNotNone(ry.mat_object._mat_object)

	def test_all(self):
		ry = Master()
		ry.load('a', 7)
		ry.r('b <- 4')
		ry.mat('d = 9;')
		with self.subTest('no repeats'):
			w = ry.who
			self.assertIs(type(w), dict)
			self.assertIn('mat', w)
			self.assertIn('r', w)
			self.assertIn('py', w)
			self.assertListEqual(w['mat'], ry.who_mat)
			self.assertListEqual(w['r'], ry.who_r)
			self.assertListEqual(w['py'], ry.who_py)
			self.assertDictEqual(ry.dump_all(), {'b':4, 'd':9})

		with self.subTest('r X mat'):
			ry.r('d <- 7')
			self.assertDictEqual(ry.dump_all(), {'b':4, 'r_d':7, 'mat_d':9})
			self.assertDictEqual(ry.dump_all('mat'), {'b':4, 'd':9})
			self.assertDictEqual(ry.dump_all('r'), {'b':4, 'd':7})
			self.assertRaisesRegex(Exception, 'Repeated variable name [a-zA-Z]+', ry.dump_all, None)

class Test_Multilang_Master_Py(unittest.TestCase):
	def setUp(self):
		self.ry = Master(r=False, mat=False)

	def test_python(self):
		with self.subTest('load'):
			self.ry.load('a',4)
		with self.subTest('who_py()'):
			self.assertListEqual(self.ry.who_py,['a'])

		with self.subTest('load_from_dict'):
			self.ry.load_from_dict({'b':4})
		with self.subTest('dump_py'):
			self.assertDictEqual(self.ry.dump_py(),{'a':4, 'b':4})

		with self.subTest('drop'):
			self.ry.drop('a')
			self.assertDictEqual(self.ry.dump_py(), {'b':4})
class Test_Multilang_Master_R(unittest.TestCase):
	def setUp(self):
		self.ry = Master(mat=False)

	def tearDown(self):
		self.ry.r_object.close()

	def test_scalar(self):
		with self.subTest('who_r, dump_r'):
			self.ry.r('a<-4')
			self.assertListEqual(self.ry.who_r, ['a'])
			self.assertDictEqual(self.ry.dump_r(), {'a':4})

		with self.subTest('py_to_r'):
			self.ry.load('b',6)
			self.ry.py_to_r('b')
			self.assertListEqual(self.ry.who_r, ['a','b'])
			self.assertDictEqual(self.ry.dump_r(), {'a':4, 'b':6})

		with self.subTest('r_to_py'):
			self.ry.r_to_py('a')
			self.assertDictEqual(self.ry.dump_py(), {'a':4, 'b':6})

	def test_array(self):
		with self.subTest('py_to_r'):
			self.ry.load('a',[1,2,3])
			self.ry.py_to_r('a')
			self.assertListEqual(self.ry.who_r, ['a'])
			d = self.ry.dump_r()
			self.assertEqual(len(d),1)
			self.assertIn('a', d)
			self.assertIs(type(d['a']), np.ndarray)
			self.assertListEqual([1,2,3], d['a'].tolist())
			del d

		with self.subTest('r_to_py'):
			self.ry.r('b <- c(2,3,4)')
			self.ry.r_to_py('b')
			d = self.ry.dump_py()
			self.assertEqual(2, len(d))
			self.assertIn('b', d)
			self.assertIs(type(d['b']), np.ndarray)
			self.assertListEqual([2,3,4], d['b'].tolist())

	def test_matrix(self):
		with self.subTest('py_to_r'):
			self.ry.load('a', [[1,2,3],[4,5,6],[7,8,9]])
			self.ry.py_to_r('a')
			self.assertListEqual(['a'], self.ry.who_r)
			d = self.ry.dump_r()
			self.assertEqual(1, len(d))
			self.assertIn('a', d)
			self.assertIs(type(d['a']), np.ndarray)
			self.assertListEqual([[1,2,3],[4,5,6],[7,8,9]], d['a'].tolist())
			del d

		with self.subTest('r_to_py'):
			self.ry.r('m <- matrix(1:9, nrow=3, ncol=3)')
			self.ry.r_to_py('m')
			d = self.ry.dump_py()
			self.assertEqual(len(d), 2)
			self.assertIn('m', d)
			self.assertIs(type(d['m']), np.ndarray)
			self.assertListEqual([[1,4,7],[2,5,8],[3,6,9]], d['m'].tolist())

	def test_multiline(self):
		with self.subTest('assignment'):
			self.ry.r('b <- matrix(1:9,\n\tnrow=3, ncol=3)')
			self.assertIn('nrow=3, ncol=3)', self.ry.r_object.before)

		with self.subTest('function'):
			self.ry.r('test <- function(x) {\n\treturn(x+2)\n}')
			self.assertIn('}', self.ry.r_object.before)

	def test_numpy(self):
		self.ry.load('a', np.array([[1,2,3],[4,5,6]]))
		self.ry.py_to_r('a')
		self.assertIn('a', self.ry.who_r)
		d = self.ry.dump_r()
		self.assertEqual(1, len(d))
		self.assertIn('a', d)
		self.assertIs(type(d['a']), np.ndarray)
		self.assertListEqual(d['a'].tolist(), [[1,2,3],[4,5,6]])


class Test_Multilang_Master_Mat(unittest.TestCase):
	def setUp(self):
		self.ry = Master(r=False)

	def tearDown(self):
		self.ry.mat_object.close()

	def test_scalar(self):
		with self.subTest('who_mat, dump_mat'):
			self.ry.mat('a = 3;')
			self.assertListEqual(self.ry.who_mat, ['a'])
			self.assertDictEqual(self.ry.dump_mat(), {'a':3})

		with self.subTest('py_to_mat'):
			self.ry.load('b',7)
			self.ry.py_to_mat('b')
			self.assertListEqual(self.ry.who_mat, ['a','b'])
			self.assertDictEqual(self.ry.dump_mat(), {'a':3, 'b':7})

		with self.subTest('mat_to_py'):
			self.ry.mat_to_py('a')
			self.assertDictEqual(self.ry.dump_py(), {'a':3, 'b':7})

	def test_array(self):
		with self.subTest('py_to_mat'):
			self.ry.load('a', [1,2,3])
			self.ry.py_to_mat('a')
			self.assertListEqual(self.ry.who_mat, ['a'])
			d = self.ry.dump_mat()
			self.assertEqual(len(d), 1)
			self.assertIn('a', d)
			self.assertIs(type(d['a']), np.ndarray)
			self.assertListEqual(d['a'].tolist(), [1,2,3])
			del d

		with self.subTest('mat_to_py'):
			self.ry.mat('b = linspace(1,5,5);')
			self.ry.mat_to_py('b')
			d = self.ry.dump_py()
			self.assertEqual(2, len(d))
			self.assertIn('b', d)
			self.assertIs(type(d['b']), np.ndarray)
			self.assertListEqual([1,2,3,4,5], d['b'].tolist())

	def test_matrix(self):
		with self.subTest('py_to_mat'):
			self.ry.load('a', [[1,2,3],[4,5,6],[7,8,9]])
			self.ry.py_to_mat('a')
			self.assertListEqual(['a'], self.ry.who_mat)
			d = self.ry.dump_mat()
			self.assertEqual(1, len(d))
			self.assertIn('a', d)
			self.assertIs(type(d['a']), np.ndarray)
			self.assertListEqual(d['a'].tolist(), [[1,2,3],[4,5,6],[7,8,9]])
			del d

		with self.subTest('mat_to_py'):
			self.ry.mat('i = eye(3);')
			self.ry.mat_to_py('i')
			d = self.ry.dump_py()
			self.assertEqual(len(d), 2)
			self.assertIn('i', d)
			self.assertIs(type(d['i']), np.ndarray)
			self.assertListEqual(d['i'].tolist(), [[1,0,0],[0,1,0],[0,0,1]])

	def test_multiline(self):
			self.ry.mat('a = [1 2 3 ...\n4 5 6];')
			self.assertEqual(self.ry.mat_object.before, 'a = [1 2 3 ...\r\n4 5 6];')


	def test_numpy(self):
		self.ry.load('a', np.array([[1,2,3],[4,5,6]]))
		self.ry.py_to_mat('a')
		self.assertIn('a', self.ry.who_mat)
		d = self.ry.dump_mat()
		self.assertEqual(1, len(d))
		self.assertIn('a', d)
		self.assertIs(type(d['a']), np.ndarray)
		self.assertListEqual(d['a'].tolist(), [[1,2,3],[4,5,6]])


class Test_Multilang_Master_RMat(unittest.TestCase):
	def setUp(self):
		self.ry = Master()

	def tearDown(self):
		self.ry.mat_object.close()
		self.ry.r_object.close()

	def test_scalar(self):
		with self.subTest('r_to_mat'):
			self.ry.r('a<-3')
			self.ry.r_to_mat('a')
			self.assertListEqual(self.ry.who_mat, self.ry.who_r)
			self.assertDictEqual(self.ry.dump_r(),self.ry.dump_mat())

		with self.subTest('mat_to_r'):
			self.ry.mat('b = 9;')
			self.ry.mat_to_r('b')
			self.assertListEqual(self.ry.who_mat, self.ry.who_r)
			self.assertDictEqual(self.ry.dump_r(), self.ry.dump_mat())

	def test_array(self):
		with self.subTest('r_to_mat'):
			self.ry.r('a <- c(1,2,3)')
			self.ry.r_to_mat('a')
			self.assertListEqual(self.ry.who_r, self.ry.who_mat)
			m = self.ry.dump_mat()
			r = self.ry.dump_r()
			self.assertIn('a', m)
			self.assertIn('a', r)
			self.assertIs(type(m['a']), type(r['a']))
			self.assertListEqual(m['a'].tolist(), r['a'].tolist())
			del m,r

		with self.subTest('mat_to_r'):
			self.ry.mat('d = linspace(1,5,5);')
			self.ry.mat_to_r('d')
			self.assertListEqual(self.ry.who_mat, self.ry.who_r)
			m = self.ry.dump_mat()
			r = self.ry.dump_r()
			self.assertIn('d', m)
			self.assertIn('d', r)
			self.assertIs(type(m['d']), type(r['d']))
			self.assertListEqual(m['d'].tolist(), r['d'].tolist())

	def test_matrix(self):
		with self.subTest('r_to_mat'):
			self.ry.r('a <- matrix(1:9, nrow=3, ncol=3)')
			self.ry.r_to_mat('a')
			self.assertListEqual(self.ry.who_mat, self.ry.who_r)
			m = self.ry.dump_mat()
			r = self.ry.dump_r()
			self.assertIn('a', m)
			self.assertIn('a', r)
			self.assertIs(type(m['a']), type(r['a']))
			self.assertListEqual(m['a'].tolist(), r['a'].tolist())
			del m,r

		with self.subTest('mat_to_r'):
			self.ry.mat('i = eye(3);')
			self.ry.mat_to_r('i')
			self.assertListEqual(self.ry.who_r, self.ry.who_mat)
			m = self.ry.dump_mat()
			r = self.ry.dump_r()
			self.assertIn('i', m)
			self.assertIn('i', r)
			self.assertIs(type(m['i']), type(r['i']))
			self.assertListEqual(m['i'].tolist(), r['i'].tolist())

if __name__ == '__main__':
	unittest.main()