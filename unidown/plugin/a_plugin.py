import logging
import pkgutil
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from time import time
from typing import Dict, List, Tuple

import certifi
import urllib3
import urllib3.util
from google.protobuf import json_format
from google.protobuf.json_format import ParseError
from packaging.version import Version
from tqdm import tqdm
from urllib3.exceptions import HTTPError

import unidown.dynamic_data as dynamic_data
from unidown.plugin.exceptions import PluginException
from unidown.plugin.link_item import LinkItem
from unidown.plugin.plugin_info import PluginInfo
from unidown.plugin.protobuf.save_state_pb2 import SaveStateProto
from unidown.plugin.save_state import SaveState
from unidown.tools import create_dir_rec, delete_dir_rec


class APlugin(ABC):
    """
    Abstract class of a plugin. Provides all needed variables and methods.

    :param info: information about the plugin
    :type info: ~unidown.plugins.data.plugin_info.PluginInfo
    :raises PluginException: can not create default plugin paths

    :ivar _info: information about the plugin, access with :func:`~unidown.plugins.a_plugin.APlugin.info`
                 **| do not edit**
    :vartype _info: ~unidown.plugins.data.plugin_info.PluginInfo
    :ivar log: use this for logging **| do not edit**
    :vartype log: ~logging.Logger
    :ivar temp_path: path where the plugin can place all temporary data **| do not edit**
    :vartype temp_path: ~pathlib.Path
    :ivar simul_downloads: number of simultaneous downloads
    :vartype simul_downloads: int
    :ivar unit: the thing which should be downloaded
    :vartype unit: str
    :ivar _download_path: general download path of the plugin **| do not edit**
    :vartype _download_path: ~pathlib.Path
    :ivar save_state_file: file which contains the latest savestate of the plugin **| do not edit**
    :vartype save_state_file: ~pathlib.Path
    :ivar downloader: downloader which will download the data **| do not edit**
    :vartype downloader: ~urllib3.HTTPSConnectionPool
    :ivar _last_update: latest update time of the referencing data, access with
                        :func:`~unidown.plugins.a_plugin.APlugin.last_update` **| do not edit**
    :vartype _last_update: ~datetime.datetime
    :ivar _download_data: referencing data, access with :func:`~unidown.plugins.a_plugin.APlugin.download_data`
                          **| do not edit**
    :vartype _download_data: dict(str, ~unidown.plugins.data.link_item.LinkItem)
    """

    def __init__(self, info: PluginInfo):
        self.log = logging.getLogger(info.name)
        self.simul_downloads = dynamic_data.USING_CORES

        self._info = info  # info about the module
        self.temp_path = dynamic_data.TEMP_DIR.joinpath(self.name)  # module temp path
        self._download_path = dynamic_data.DOWNLOAD_DIR.joinpath(self.name)  # module download path
        self.save_state_file = dynamic_data.SAVESTAT_DIR.joinpath(self.name + '_save.json')  # module save path

        try:
            create_dir_rec(self.temp_path)
            create_dir_rec(self._download_path)
        except PermissionError:
            raise PluginException('Can not create default plugin paths, due to a permission error.')

        self._last_update = datetime(1970, 1, 1)
        self._download_data = {}
        self.unit = 'item'
        self.downloader = urllib3.HTTPSConnectionPool(self.info.host, maxsize=self.simul_downloads,
                                                      cert_reqs='CERT_REQUIRED', ca_certs=certifi.where())

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, self.__class__):
            return False
        return self.info == other.info

    def __ne__(self, other: object) -> bool:
        return not self.__eq__(other)

    @property
    def info(self) -> PluginInfo:
        """
        Information about the plugin.

        :rtype: ~unidown.plugins.data.plugin_info.PluginInfo
        """
        return self._info

    @property
    def host(self) -> str:
        """
        Host url.

        :rtype: str
        """
        return self._info.host

    @property
    def name(self) -> str:
        """
        Plugin name.

        :rtype: str
        """
        return self._info.name

    @property
    def version(self) -> Version:
        """
        Plugin version, PEP440 is used.

        :rtype: ~packaging.version.Version
        """
        return self._info.version

    @property
    def last_update(self) -> datetime:
        """
        Newest update time of the plugins referenced data.

        :rtype: ~datetime.datetime
        """
        return self._last_update

    @property
    def download_data(self) -> Dict[str, LinkItem]:
        """
        Plugins referenced data.

        :rtype: Dict[str, ~unidown.plugins.data.link_item.LinkItem]
        """
        return self._download_data

    @property
    def download_path(self) -> Path:
        """
        General download path of the plugin.

        :rtype: ~pathlib.Path
        """
        return self._download_path

    @abstractmethod
    def _create_download_links(self) -> Dict[str, LinkItem]:
        """
        Get the download links in a specific format.
        **Has to be implemented inside Plugins.**

        :rtype: Dict(str, ~unidown.plugins.data.link_item.LinkItem)
        :raises NotImplementedError: abstract method
        """
        raise NotImplementedError

    @abstractmethod
    def _create_last_update_time(self) -> datetime:
        """
        Get the newest update time from the referencing data.
        **Has to be implemented inside Plugins.**

        :rtype: ~datetime.datetime
        :raises NotImplementedError: abstract method
        """
        raise NotImplementedError

    def update_last_update(self):
        """
        Call this to update the latest update time. Calls :func:`~unidown.plugins.a_plugin.APlugin._create_last_update`.
        """
        self._last_update = self._create_last_update_time()

    def update_download_links(self):
        """
        Update the download links. Calls :func:`~unidown.plugins.a_plugin.APlugin._create_download_data`.
        """
        self._download_data = self._create_download_links()

    # TODO: parallelize?
    def check_download(self, link_item_dict: Dict[str, LinkItem], folder: Path, log: bool = True) -> Tuple[
        Dict[str, LinkItem], Dict[str, LinkItem]]:
        """
        Check if the download of the given dict was successful. No proving if the content of the file is correct too.

        :param link_item_dict: dict which to check
        :type link_item_dict: dict(str, ~unidown.plugins.data.link_item.LinkItem)
        :param folder: folder where the downloads are saved
        :type folder: ~pathlib.Path
        :param log: if the lost items should be logged
        :type log: bool
        :return: succeeded and lost dicts
        :rtype: dict(str, ~unidown.plugins.data.link_item.LinkItem), dict(str, ~unidown.plugins.data.link_item.LinkItem)
        """
        succeed = {link: item for link, item in link_item_dict.items() if folder.joinpath(item.name).is_file()}
        lost = {link: item for link, item in link_item_dict.items() if link not in succeed}

        if lost and log:
            for link, item in lost.items():
                self.log.error('Not downloaded: {url} - {name}'.format(url=self.info.host + link, name=item.name))

        return succeed, lost

    def clean_up(self):
        """
        Default clean up for a module.
        Deletes :attr:`~unidown.plugins.a_plugin.APlugin.temp_path`.
        """
        if self.downloader.pool is not None:  # TODO: remove if new urrlib3 version comes out
            self.downloader.close()
        delete_dir_rec(self.temp_path)

    def delete_data(self):
        """
        Delete everything which is related to the plugin. **Do not use if you do not know what you do!**
        """
        self.clean_up()
        delete_dir_rec(self._download_path)
        if self.save_state_file.exists():
            self.save_state_file.unlink()

    def download_as_file(self, url: str, folder: Path, name: str, delay: float = 0) -> str:
        """
        Download the given url to the given target folder.

        :param url: link
        :type url: str
        :param folder: target folder
        :type folder: ~pathlib.Path
        :param name: target file name
        :param delay: after download wait in seconds
        :type name: str
        :return: url
        :rtype: str
        :raises ~urllib3.exceptions.HTTPError: if the connection has an error
        """
        while folder.joinpath(name).exists():  # TODO: handle already existing files
            self.log.warning('already exists: ' + name)
            name = name + '_d'

        with self.downloader.request('GET', url, preload_content=False, retries=urllib3.util.retry.Retry(3)) as reader:
            if reader.status == 200:
                with folder.joinpath(name).open(mode='wb') as out_file:
                    out_file.write(reader.data)
            else:
                raise HTTPError("{url} | {status}".format(url=url, status=str(reader.status)))

        if delay > 0:
            time.sleep(delay)

        return url

    def download(self, link_item_dict: Dict[str, LinkItem], folder: Path, desc: str, unit: str, delay: float = 0) -> \
            List[str]:
        """
        Download the given LinkItem dict from the plugins host, to the given path. Proceeded with multiple connections
        :attr:`~unidown.a_plugin.APlugin.simul_downloads`. After
        :func:`~unidown.plugins.a_plugin.APlugin.check_download` is recommend.

        :param link_item_dict: data which gets downloaded
        :type link_item_dict: dict(str, ~unidown.plugins.data.link_item.LinkItem)
        :param folder: target download folder
        :type folder: ~pathlib.Path
        :param desc: description of the progressbar
        :type desc: str
        :param unit: unit of the download, shown in the progressbar
        :type unit: str
        :param delay: delay between the downloads in seconds
        :type delay: int
        :return: list of urls of downloads without errors
        :rtype: list[str]
        """
        # TODO: add other optional host?
        if not link_item_dict:
            return []

        job_list = []
        with ThreadPoolExecutor(max_workers=self.simul_downloads) as executor:
            for link, item in link_item_dict.items():
                job = executor.submit(self.download_as_file, link, folder, item.name, delay)
                job_list.append(job)

            pbar = tqdm(as_completed(job_list), total=len(job_list), desc=desc, unit=unit, leave=True, mininterval=1,
                        ncols=100, disable=dynamic_data.DISABLE_TQDM)
            for iteration in pbar:
                pass

        download_without_errors = []
        for job in job_list:
            try:
                download_without_errors.append(job.result())
            except HTTPError as ex:
                self.log.warning("Failed to download: " + str(ex))
                # Todo: connection lost handling (check if the connection to the server itself is lost)

        return download_without_errors

    def _create_save_state(self, link_item_dict: Dict[str, LinkItem]) -> SaveState:
        """
        Create protobuf savestate of the module and the given data.

        :param link_item_dict: data
        :type link_item_dict: dict(str, ~unidown.plugins.data.link_item.LinkItem)
        :rtype: ~unidown.plugins.data.save_state.SaveState
        """
        return SaveState(dynamic_data.SAVE_STATE_VERSION, self.info, self.last_update, link_item_dict)

    def save_save_state(self, data_dict: Dict[str, LinkItem]):  # TODO: add progressbar
        """
        Save meta data about the downloaded things and the plugin to file.

        :param data_dict: data
        :type data_dict: dict(link, ~unidown.plugins.data.link_item.LinkItem)
        """
        json_data = json_format.MessageToJson(self._create_save_state(data_dict).to_protobuf())
        with self.save_state_file.open(mode='w', encoding="utf8") as writer:
            writer.write(json_data)

    def load_save_state(self) -> SaveState:
        """
        Load the savestate of the plugin.

        :return: savestate
        :rtype: ~unidown.plugins.data.save_state.SaveState
        :raises ~unidown.plugins.exceptions.PluginException: broken savestate json
        :raises ~unidown.plugins.exceptions.PluginException: different savestate versions
        :raises ~unidown.plugins.exceptions.PluginException: different plugin versions
        :raises ~unidown.plugins.exceptions.PluginException: different plugin names
        :raises ~unidown.plugins.exceptions.PluginException: could not parse the protobuf
        """
        if not self.save_state_file.exists():
            self.log.info("No savestate file found.")
            return SaveState(dynamic_data.SAVE_STATE_VERSION, self.info, datetime(1970, 1, 1), {})

        savestat_proto = ""
        with self.save_state_file.open(mode='r', encoding="utf8") as data_file:
            try:
                savestat_proto = json_format.Parse(data_file.read(), SaveStateProto(), ignore_unknown_fields=False)
            except ParseError:
                raise PluginException(
                    "Broken savestate json. Please fix or delete (you may lose data in this case) the file: {path}"
                    "".format(path=self.save_state_file))

        try:
            save_state = SaveState.from_protobuf(savestat_proto)
        except ValueError as ex:
            raise PluginException("Could not parse the protobuf {path}: {msg}".format(path=self.save_state_file,
                                                                                      msg=str(ex)))
        else:
            del savestat_proto

        if save_state.version != dynamic_data.SAVE_STATE_VERSION:
            raise PluginException("Different save state version handling is not implemented yet.")

        if save_state.plugin_info.version != self.info.version:
            raise PluginException("Different plugin version handling is not implemented yet.")

        if save_state.plugin_info.name != self.name:
            raise PluginException("Save state plugin ({name}) does not match the current ({cur_name}).".format(
                name=save_state.plugin_info.name, cur_name=self.name))
        return save_state

    def get_updated_data(self, old_data: Dict[str, LinkItem]) -> Dict[str, LinkItem]:
        """
        Get links who needs to be downloaded by comparing old and the new data
        :func:`~unidown.plugins.a_plugin.APlugin.download_data`.

        :param old_data: old data
        :type old_data: dict(str, ~unidown.plugins.data.link_item.LinkItem)
        :return: data which is newer or dont exist in the old one
        :rtype: dict(str, ~unidown.plugins.data.link_item.LinkItem)
        """
        if not self.download_data:
            return {}
        new_link_item_dict = {}
        for link, link_item in tqdm(self.download_data.items(), desc="Compare with save", unit="item", leave=True,
                                    mininterval=1, ncols=100, disable=dynamic_data.DISABLE_TQDM):
            # TODO: add methode to log lost items, which are in old but not in new
            if link in new_link_item_dict:  # TODO: is ever false, since its the key of a dict: move to the right place
                self.log.warning("Duplicate: " + link + " - " + new_link_item_dict[link] + " : " + link_item)

            # if the new_data link does not exists in old_data or new_data time is newer
            if (link not in old_data) or (link_item.time > old_data[link].time):
                new_link_item_dict[link] = link_item

        return new_link_item_dict

    def update_dict(self, base: Dict[str, LinkItem], new: Dict[str, LinkItem]):
        """
        Use for updating save state dicts and get the new save state dict. Provides a debug option at info level.
        Updates the base dict. Basically executes `base.update(new)`.

        :param base: base dict **gets overridden!**
        :type base: dict(str, ~unidown.plugins.data.link_item.LinkItem)
        :param new: data which updates the base
        :type new: dict(str, ~unidown.plugins.data.link_item.LinkItem)
        """
        if logging.INFO >= logging.getLevelName(dynamic_data.LOG_LEVEL):  # TODO: logging here or outside
            for link, item in new.items():
                if link in base:
                    self.log.info('Actualize item: ' + link + ' | ' + str(base[link]) + ' -> ' + str(item))
        base.update(new)


def get_plugins() -> List[str]:
    """
    Get all existing plugins inside the :py:mod:`unidown.plugins`.

    :rtype: list[str]
    """
    import unidown.plugins

    package = unidown.plugins
    return [modname for _, modname, ispkg in pkgutil.iter_modules(path=package.__path__, prefix=package.__name__ + '.')]
