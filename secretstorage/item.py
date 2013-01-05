# SecretStorage module for Python
# Access passwords using the SecretService DBus API
# Author: Dmitry Shachnev, 2013
# License: BSD

"""SecretStorage item contains a *secret*, some *attributes* and a
*label* visible to user. Editing all these properties and reading the
secret is possible only when the :doc:`collection <collection>` storing
the item is unlocked. The collection can be unlocked using Collection's
:meth:`secretstorage.collection.Collection.unlock` method."""

import dbus
from secretstorage.defines import SECRETS, SS_PREFIX
from secretstorage.exceptions import LockedException
from secretstorage.util import *

ITEM_IFACE = SS_PREFIX + 'Item'
DEFAULT_COLLECTION = '/org/freedesktop/secrets/aliases/default'

class Item(object):
	"""Represents a secret item."""

	def __init__(self, bus, item_path, session=None):
		if isinstance(item_path, int):
			# An item id was specified instead of the path
			item_path = '%s/%d' % (DEFAULT_COLLECTION, item_path)
		self.item_path = item_path
		try:
			item_obj = bus.get_object(SECRETS, item_path)
		except dbus.exceptions.DBusException as e:
			if e.get_dbus_name() == DBUS_SERVICE_UNKNOWN:
				raise SecretServiceNotAvailableException(e.get_dbus_message())
			raise
		self.session = session
		self.bus = bus
		self.item_iface = InterfaceWrapper(item_obj, ITEM_IFACE)
		self.item_props_iface = InterfaceWrapper(item_obj,
			dbus.PROPERTIES_IFACE)
		self.item_props_iface.Get(ITEM_IFACE, 'Label')

	def __eq__(self, other):
		return (self._item_id() == other._item_id()) \
		and (self.get_attributes() == other.get_attributes())

	def _item_id(self):
		return int(self.item_path.rsplit('/', 1)[1])

	def is_locked(self):
		"""Returns ``True`` if item is locked, otherwise ``False``."""
		return bool(self.item_props_iface.Get(ITEM_IFACE, 'Locked'))

	def ensure_not_locked(self):
		"""If collection is locked, raises
		:exc:`~secretstorage.exceptions.LockedException`."""
		if self.is_locked():
			raise LockedException('Item is locked!')

	def get_attributes(self):
		"""Returns item attributes (dictionary)."""
		attrs = self.item_props_iface.Get(ITEM_IFACE, 'Attributes')
		return dict([(to_unicode(key), to_unicode(value))
			for key, value in attrs.items()])

	def set_attributes(self, attributes):
		"""Sets item attributes to `attributes` (dictionary)."""
		self.item_props_iface.Set(ITEM_IFACE, 'Attributes', attributes)

	def get_label(self):
		"""Returns item label (unicode string)."""
		label = self.item_props_iface.Get(ITEM_IFACE, 'Label')
		return to_unicode(label)

	def set_label(self, label):
		"""Sets item label to `label`."""
		self.ensure_not_locked()
		self.item_props_iface.Set(ITEM_IFACE, 'Label', label)

	def delete(self):
		"""Deletes the item."""
		self.ensure_not_locked()
		return self.item_iface.Delete()

	def get_secret(self):
		"""Returns item secret (bytestring)."""
		self.ensure_not_locked()
		if not self.session:
			self.session = open_session(self.bus)
		secret = self.item_iface.GetSecret(self.session)
		return bytes(bytearray(secret[2]))

	def set_secret(self, secret):
		"""Sets item secret to `secret`."""
		self.ensure_not_locked()
		if not self.session:
			self.session = open_session(self.bus)
		secret = format_secret(secret, self.session)
		self.item_iface.SetSecret(secret)

	def to_tuple(self):
		"""Returns (*attributes*, *secret*) tuple representing the
		item."""
		self.ensure_not_locked()
		return self.get_attributes(), self.get_secret()
