【代码导入】
		直接在openstack havana neutron的neutron\plugins\ml2\drivers目录下，
	导入该目录即可
	
【配置说明】
1、将controller节点的/etc/default/neutron-server 文件修改为 NEUTRON_PLUGIN_CONFIG="/etc/neutron/plugins/ml2/ml2_conf.ini"
2、注册huawei driver 在中加入/usr/share/pyshared/neutron-2013.2.egg-info/entry_points.txt
	huawei = neutron.plugins.ml2.drivers.huawei.mechanism_huawei:HuaweiDriver
3、在中配置/etc/neutron/plugins/ml2/ml2_conf.ini 
   mechanism_drivers = huawei
   vni_ranges = 4097:5000
