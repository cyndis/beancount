__author__ = "Martin Blais <blais@furius.ca>"

import re

from beancount.core import inventory
from beancount.core import data
from beancount.core import amount
from beancount.core import realization
from beancount.loader import loaddoc
from beancount.ops import pad
from beancount.ops import balance
from beancount.parser import cmptest


class TestPadding(cmptest.TestCase):

    @loaddoc
    def test_pad_simple(self, entries, errors, __):
        """

          2013-05-01 open Assets:Checking
          2013-05-01 open Equity:Opening-Balances

          ;; Test the simple case that this directive generates a padding entry.
          2013-05-01 pad Assets:Checking Equity:Opening-Balances

          2013-05-03 balance Assets:Checking                                 172.45 USD

        """
        self.assertFalse(errors)
        self.assertEqualEntries("""

          2013-05-01 open Assets:Checking
          2013-05-01 open Equity:Opening-Balances

          2013-05-01 pad Assets:Checking Equity:Opening-Balances

          ;; Check this is inserted.
          2013-05-01 P "(Padding inserted for Balance of 172.45 USD for difference 172.45 USD)"
            Assets:Checking                                                        172.45 USD
            Equity:Opening-Balances                                                -172.45 USD

          2013-05-03 balance Assets:Checking                                 172.45 USD

        """, entries)


    @loaddoc
    def test_pad_no_overflow(self, entries, errors, __):
        """

          2013-05-01 open Assets:Checking
          2013-05-01 open Assets:Cash
          2013-05-01 open Equity:Opening-Balances

          ;; Pad before the next check.
          2013-05-01 pad Assets:Checking Equity:Opening-Balances

          ;; The check that is being padded.
          2013-05-03 balance Assets:Checking                                 172.45 USD

          2013-05-15 * "Add 20$"
            Assets:Checking                                                   20.00 USD
            Assets:Cash                                                      -20.00 USD

          ;; This is the next check, should not have been padded.
          2013-06-01 balance Assets:Checking                                 200.00 USD

        """
        self.assertEqual([balance.BalanceError], list(map(type, errors)))
        self.assertEqualEntries("""

          2013-05-01 open Assets:Checking
          2013-05-01 open Assets:Cash
          2013-05-01 open Equity:Opening-Balances

          2013-05-01 pad Assets:Checking Equity:Opening-Balances

          2013-05-01 P "(Padding inserted for Balance of 172.45 USD for difference 172.45 USD)"
            Assets:Checking                                                        172.45 USD
            Equity:Opening-Balances                                                -172.45 USD

          2013-05-03 balance Assets:Checking                                 172.45 USD

          2013-05-15 * "Add 20$"
            Assets:Checking                                                         20.00 USD
            Assets:Cash                                                            -20.00 USD

          2013-06-01 balance Assets:Checking                                 200.00 USD

        """, entries)

    @loaddoc
    def test_pad_used_twice_legally(self, entries, errors, __):
        """

          2013-05-01 open Assets:Checking
          2013-05-01 open Assets:Cash
          2013-05-01 open Equity:Opening-Balances

          ;; First pad.
          2013-05-01 pad  Assets:Checking   Equity:Opening-Balances

          2013-05-03 balance Assets:Checking   172.45 USD

          2013-05-15 txn "Add 20$"
            Assets:Checking             20 USD
            Assets:Cash

          ;; Second pad.
          2013-05-20 pad  Assets:Checking   Equity:Opening-Balances

          2013-06-01 balance Assets:Checking   200 USD

        """
        self.assertFalse(errors)
        self.assertEqualEntries("""

          2013-05-01 open Assets:Checking
          2013-05-01 open Assets:Cash
          2013-05-01 open Equity:Opening-Balances

          2013-05-01 pad Assets:Checking Equity:Opening-Balances

          2013-05-01 P "(Padding inserted for Balance of 172.45 USD for difference 172.45 USD)"
            Assets:Checking                                                        172.45 USD
            Equity:Opening-Balances                                                -172.45 USD

          2013-05-03 balance Assets:Checking                                 172.45 USD

          2013-05-15 * "Add 20$"
            Assets:Checking                                                         20.00 USD
            Assets:Cash                                                            -20.00 USD

          2013-05-20 pad Assets:Checking Equity:Opening-Balances

          2013-05-20 P "(Padding inserted for Balance of 200.00 USD for difference 7.55 USD)"
            Assets:Checking                                                          7.55 USD
            Equity:Opening-Balances                                                  -7.55 USD

          2013-06-01 balance Assets:Checking                                 200.00 USD

        """, entries)

    @loaddoc
    def test_pad_used_twice_illegally(self, entries, errors, __):
        """

          2013-05-01 open Assets:Checking
          2013-05-01 open Equity:Opening-Balances

          2013-05-03 balance Assets:Checking   0.00 USD

          ;; Two pads in between checks.
          2013-05-10 pad  Assets:Checking   Equity:Opening-Balances
          2013-05-20 pad  Assets:Checking   Equity:Opening-Balances

          2013-06-01 balance Assets:Checking   200 USD

        """
        self.assertEqual([pad.PadError], list(map(type, errors)))
        self.assertEqualEntries("""

          2013-05-01 open Assets:Checking
          2013-05-01 open Equity:Opening-Balances

          2013-05-03 balance Assets:Checking                                 0.00 USD

          2013-05-10 pad Assets:Checking Equity:Opening-Balances

          2013-05-20 pad Assets:Checking Equity:Opening-Balances

          2013-05-20 P "(Padding inserted for Balance of 200.00 USD for difference 200.00 USD)"
            Assets:Checking                                                        200.00 USD
            Equity:Opening-Balances                                                -200.00 USD

          2013-06-01 balance Assets:Checking                                 200.00 USD

        """, entries)

    @loaddoc
    def test_pad_unused(self, entries, errors, __):
        """

          2013-05-01 open Assets:Checking
          2013-05-01 open Assets:Cash
          2013-05-01 open Equity:Opening-Balances

          2013-05-10 * "Add 200$"
            Assets:Checking       200.00 USD
            Assets:Cash          -200.00 USD

          ;; This pad will do nothing, should raise a warning..
          2013-05-20 pad  Assets:Checking   Equity:Opening-Balances

          2013-06-01 balance Assets:Checking   200.0 USD

        """
        self.assertEqual([pad.PadError], list(map(type, errors)))
        self.assertEqualEntries("""

          2013-05-01 open Assets:Checking
          2013-05-01 open Assets:Cash
          2013-05-01 open Equity:Opening-Balances

          2013-05-10 * "Add 200$"
            Assets:Checking                                                        200.00 USD
            Assets:Cash                                                           -200.00 USD

          2013-05-20 pad Assets:Checking Equity:Opening-Balances

          2013-06-01 balance Assets:Checking                                 200.00 USD

        """, entries)

    @loaddoc
    def test_pad_parents(self, entries, errors, __):
        """

          2013-05-01 open Assets:US
          2013-05-01 open Assets:US:Bank1:Checking
          2013-05-01 open Assets:US:Bank1:Savings
          2013-05-01 open Assets:US:Bank2:Checking
          2013-05-01 open Assets:US:Bank2:Savings
          2013-05-01 open Equity:Opening-Balances

          2013-05-10 *
            Assets:US:Bank1:Checking                                 1.00 USD
            Assets:US:Bank1:Savings                                  2.00 USD
            Assets:US:Bank2:Checking                                 3.00 USD
            Assets:US:Bank2:Savings                                  4.00 USD
            Equity:Opening-Balances                                 -10.00 USD

          2013-05-20 pad Assets:US Equity:Opening-Balances

          2013-06-01 balance Assets:US                                       100.00 USD

        """
        self.assertFalse(errors)
        self.assertEqualEntries("""

          2013-05-01 open Assets:US
          2013-05-01 open Assets:US:Bank1:Checking
          2013-05-01 open Assets:US:Bank1:Savings
          2013-05-01 open Assets:US:Bank2:Checking
          2013-05-01 open Assets:US:Bank2:Savings
          2013-05-01 open Equity:Opening-Balances

          2013-05-10 *
            Assets:US:Bank1:Checking                                                 1.00 USD
            Assets:US:Bank1:Savings                                                  2.00 USD
            Assets:US:Bank2:Checking                                                 3.00 USD
            Assets:US:Bank2:Savings                                                  4.00 USD
            Equity:Opening-Balances                                                 -10.00 USD

          2013-05-20 pad Assets:US Equity:Opening-Balances

          ;; A single pad that does not include child accounts should be inserted.
          2013-05-20 P "(Padding inserted for Balance of 100.00 USD for difference 90.00 USD)"
            Assets:US                                                              90.00 USD
            Equity:Opening-Balances                                                -90.00 USD

          2013-06-01 balance Assets:US                                       100.00 USD

        """, entries)

    @loaddoc
    def test_pad_multiple_currencies(self, entries, errors, __):
        """
          2013-05-01 open Assets:Checking
          2013-05-01 open Equity:Opening-Balances

          2013-05-10 *
            Assets:Checking                     1.00 USD
            Assets:Checking                     1.00 CAD
            Assets:Checking                     1.00 EUR
            Equity:Opening-Balances

          ;; This should insert two entries: one for USD, one for CAD (different
          ;; amount) and none for EUR.
          2013-05-20 pad Assets:Checking Equity:Opening-Balances

          2013-06-01 balance Assets:Checking    5.00 USD
          2013-06-01 balance Assets:Checking    3.00 CAD
          2013-06-01 balance Assets:Checking    1.00 EUR

        """
        self.assertFalse(errors)
        self.assertEqualEntries("""

          2013-05-01 open Assets:Checking
          2013-05-01 open Equity:Opening-Balances

          2013-05-10 *
            Assets:Checking                                                          1.00 USD
            Assets:Checking                                                          1.00 CAD
            Assets:Checking                                                          1.00 EUR
            Equity:Opening-Balances                                                  -1.00 USD
            Equity:Opening-Balances                                                  -1.00 CAD
            Equity:Opening-Balances                                                  -1.00 EUR

          2013-05-20 pad Assets:Checking Equity:Opening-Balances

          2013-05-20 P "(Padding inserted for Balance of 5.00 USD for difference 4.00 USD)"
            Assets:Checking                                                          4.00 USD
            Equity:Opening-Balances                                                  -4.00 USD

          2013-05-20 P "(Padding inserted for Balance of 3.00 CAD for difference 2.00 CAD)"
            Assets:Checking                                                          2.00 CAD
            Equity:Opening-Balances                                                  -2.00 CAD

          2013-06-01 balance Assets:Checking                                 5.00 USD
          2013-06-01 balance Assets:Checking                                 3.00 CAD
          2013-06-01 balance Assets:Checking                                 1.00 EUR

        """, entries)

    @loaddoc
    def test_pad_check_balances(self, entries, errors, __):
        """
          2013-05-01 open Assets:Checking
          2013-05-01 open Assets:Cash
          2013-05-01 open Equity:Opening-Balances

          2013-05-01 pad  Assets:Checking   Equity:Opening-Balances

          2013-05-03 txn "Add 20$"
            Assets:Checking                        10 USD
            Assets:Cash

          2013-05-10 balance Assets:Checking      105 USD

          2013-05-15 txn "Add 20$"
            Assets:Checking                        20 USD
            Assets:Cash

          2013-05-16 txn "Add 20$"
            Assets:Checking                        20 USD
            Assets:Cash

          2013-06-01 balance Assets:Checking      145 USD

        """
        post_map = realization.postings_by_account(entries)
        postings = post_map['Assets:Checking']

        balances = []
        pad_balance = inventory.Inventory()
        for posting in postings:
            if isinstance(posting, data.Posting):
                position_, _ = pad_balance.add_position(posting.position)
                self.assertFalse(position_.is_negative_at_cost())
            balances.append((type(posting), pad_balance.get_units('USD')))

        self.assertEqual(balances, [(data.Open, amount.from_string('0.00 USD')),
                                    (data.Pad, amount.from_string('0.00 USD')),
                                    (data.Posting, amount.from_string('95.00 USD')),
                                    (data.Posting, amount.from_string('105.00 USD')),
                                    (data.Balance, amount.from_string('105.00 USD')),
                                    (data.Posting, amount.from_string('125.00 USD')),
                                    (data.Posting, amount.from_string('145.00 USD')),
                                    (data.Balance, amount.from_string('145.00 USD'))])

    # Note: You could try padding A into B and B into A to see if it works.

    @loaddoc
    def test_pad_multiple_times(self, entries, errors, __):
        """
          2013-05-01 open Assets:Checking
          2013-05-01 open Equity:Opening-Balances

          2013-06-01 pad Assets:Checking Equity:Opening-Balances
          2013-07-01 pad Assets:Checking Equity:Opening-Balances

          2013-10-01 balance Assets:Checking    5.00 USD
        """
        self.assertEqual([pad.PadError], list(map(type, errors)))

    @loaddoc
    def test_pad_at_cost(self, entries, errors, __):
        """
          2013-05-01 open Assets:Investments
          2013-05-01 open Equity:Opening-Balances

          2013-05-15 *
            Assets:Investments   10 MSFT {54.30 USD}
            Equity:Opening-Balances

          2013-06-01 pad Assets:Investments Equity:Opening-Balances

          2013-10-01 balance Assets:Investments   12 MSFT
        """
        self.assertEqual([pad.PadError], list(map(type, errors)))
        self.assertTrue(re.search('Attempt to pad an entry with cost for',
                                  errors[0].message))
