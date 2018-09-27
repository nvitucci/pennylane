# Copyright 2018 Xanadu Quantum Technologies Inc.

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
Unit tests for CV circuit gradients.
"""
import unittest
import logging as log
log.getLogger()

import numpy as np

import strawberryfields as sf
import openqml as qm

from defaults import openqml_sf as qmsf, BaseTest


class BasicTests(BaseTest):
    "Tests for CV circuit gradients."
    def setUp(self):
        self.dev = qm.device('strawberryfields.gaussian', wires=2)
        #self.dev = qm.device('strawberryfields.fock', wires=2, cutoff_dim=10)

    def test_cv_displacement(self):
        """Test the partial derivatives of displacement gates."""
        log.info('test_cv_displacement')

        def circuit(x):
            qm.Displacement(x, 0, wires=0)
            qm.Displacement(2*x, 0, wires=1)
            return qm.expectation.PhotonNumber(0), qm.expectation.X(1)

        par = [0.4]
        q = qm.QNode(circuit, self.dev)
        #val = q.evaluate(par)
        #print('value:', val)
        grad_F  = q.gradient(par, method='F')
        grad_A  = q.gradient(par, method='A')
        grad_A2 = q.gradient(par, method='A', force_order2=True)

        # analytic method works for every parameter
        self.assertTrue(q.grad_method_for_par == {0:'A'})
        # the different methods agree
        self.assertAllAlmostEqual(grad_A, grad_F, delta=self.tol)
        self.assertAllAlmostEqual(grad_A2, grad_F, delta=self.tol)


    def test_cv_beamsplitter(self):
        """Test the partial derivatives of beamsplitter gates."""
        log.info('test_cv_beamsplitter')

        def circuit(x):
            qm.Displacement(0.4, 0, wires=0)
            qm.Beamsplitter(x, 0, wires=[0,1])
            return qm.expectation.PhotonNumber(0), qm.expectation.X(1)

        par = [0.2 * np.pi]
        q = qm.QNode(circuit, self.dev)
        val = q.evaluate(par)
        print('value:', val)
        grad_F  = q.gradient(par, method='F')
        grad_A  = q.gradient(par, method='A')
        grad_A2 = q.gradient(par, method='A', force_order2=True)
        print(grad_F)
        print(grad_A2)

        # analytic method works for every parameter
        self.assertTrue(q.grad_method_for_par == {0:'A'})
        # the different methods agree
        self.assertAllAlmostEqual(grad_A, grad_F, delta=self.tol)
        self.assertAllAlmostEqual(grad_A2, grad_F, delta=self.tol)


    def test_cv_multiple_gate_parameters(self):
        "Tests that gates with multiple free parameters yield correct gradients."
        log.info('test_cv_multiple_gate_parameters')
        par = [0.4, -0.3, -0.7]

        def qf(x, y, z):
            qm.Displacement(x, 0.2, [0])
            qm.Squeezing(y, z, [0])
            qm.Rotation(-0.2, [0])
            return qm.expectation.X(0)

        q = qm.QNode(qf, self.dev)
        grad_F = q.gradient(par, method='F')
        grad_A = q.gradient(par, method='A')
        grad_A2 = q.gradient(par, method='A', force_order2=True)

        # analytic method works for every parameter
        self.assertTrue(q.grad_method_for_par == {0:'A', 1:'A', 2:'A'})
        # the different methods agree
        self.assertAllAlmostEqual(grad_A, grad_F, delta=self.tol)
        self.assertAllAlmostEqual(grad_A2, grad_F, delta=self.tol)


    def test_cv_repeated_gate_parameters(self):
        "Tests that repeated use of a free parameter in a multi-parameter gate yield correct gradients."
        log.info('test_cv_repeated_gate_parameters')
        par = [0.2, 0.3]

        def qf(x, y):
            qm.Displacement(x, 0, [0])
            qm.Squeezing(y, -1.3*y, [0])
            return qm.expectation.X(0)

        q = qm.QNode(qf, self.dev)
        grad_F = q.gradient(par, method='F')
        grad_A = q.gradient(par, method='A')
        grad_A2 = q.gradient(par, method='A', force_order2=True)

        # analytic method works for every parameter
        self.assertTrue(q.grad_method_for_par == {0:'A', 1:'A'})
        # the different methods agree
        self.assertAllAlmostEqual(grad_A, grad_F, delta=self.tol)
        self.assertAllAlmostEqual(grad_A2, grad_F, delta=self.tol)


    def test_cv_parameters_inside_array(self):
        "Tests that free parameters inside an array passed to an Operation yield correct gradients."
        log.info('test_cv_parameters_inside_array')
        par = [0.4, 1.3]

        def qf(x, y):
            qm.Displacement(0.5, 0, [0])
            qm.Squeezing(x, 0, [0])
            M = np.zeros((5, 5), dtype=object)
            M[1,1] = y
            M[1,2] = 1.0
            M[2,1] = 1.0
            return qm.expectation.Poly(M, [0, 1])

        q = qm.QNode(qf, self.dev)
        grad = q.gradient(par)
        grad_F = q.gradient(par, method='F')
        grad_A = q.gradient(par, method='B')
        grad_A2 = q.gradient(par, method='B', force_order2=True)

        # par[0] can use the 'A' method, par[1] cannot
        self.assertTrue(q.grad_method_for_par == {0:'A', 1:'F'})
        # the different methods agree
        self.assertAllAlmostEqual(grad, grad_F, delta=self.tol)


    def test_cv_fanout(self):
        "Tests that qnodes can compute the correct function when the same parameter is used in multiple gates."
        log.info('test_cv_fanout')
        par = [0.5, 1.3]

        def circuit(x, y):
            qm.Displacement(x, 0, [0])
            qm.Rotation(y, [0])
            qm.Displacement(0, x, [0])
            return qm.expectation.X(0)

        q = qm.QNode(circuit, self.dev)
        grad_F = q.gradient(par, method='F')
        grad_A = q.gradient(par, method='A')
        grad_A2 = q.gradient(par, method='A', force_order2=True)

        # analytic method works for every parameter
        self.assertTrue(q.grad_method_for_par == {0:'A', 1:'A'})
        # the different methods agree
        self.assertAllAlmostEqual(grad_A, grad_F, delta=self.tol)
        self.assertAllAlmostEqual(grad_A2, grad_F, delta=self.tol)



if __name__ == '__main__':
    # run the tests in this file
    suite = unittest.TestSuite()
    for t in (BasicTests,):
        ttt = unittest.TestLoader().loadTestsFromTestCase(t)
        suite.addTests(ttt)

    unittest.TextTestRunner().run(suite)
