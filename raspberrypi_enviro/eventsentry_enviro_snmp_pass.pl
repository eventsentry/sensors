#!/usr/bin/perl
#
# Requirements
# ============
# Raspberry Pi with "enviro" environment sensor (https://shop.pimoroni.com/products/enviro?variant=31155658457171)
# eventsentry_enviro.py (queries "enviro" sensors and stors current readings in temp files
#
# snmpd
# The following line needs to be added to snmpd (path can be changed)
# pass .1.3.6.1.4.1.21600.1.5.1.1.1 /usr/bin/perl /home/pi/eventsentry_enviro_snmp_pass.pl
#
# Description
# ===========
# This file is called by snmpd and returns the current readings for temperature, humidity and light

$placeRoot  = ".1.3.6.1.4.1.21600.1.5.1";
$place      = ".1.3.6.1.4.1.21600.1.5.1.1.1";
$tableStart = ".1.3.6.1.4.1.21600.1.5.1.1.1.1.1";

$req = $ARGV[1];                      # Requested OID

sub getValue
{
    my $filename = shift;
    
    open FILE, $filename;
    chomp(my $line = <FILE>);
    close FILE;
    
    return $line;
}

# Debugging
#
# if ($ARGV[0] eq "-s") {
  # open  LOG,">>/tmp/espasstest.log";
  # print LOG "@ARGV\n";
  # close LOG;
  # exit 0;
# }

#  GETNEXT requests - determine next valid instance
#
if ($ARGV[0] eq "-n") 
{
    if ($req eq $place)                 { $ret = $tableStart; }
    elsif   ($req eq "$placeRoot")      { $ret = $tableStart; }
    elsif   ($req eq "$placeRoot.1")    { $ret = $tableStart; }
    elsif   ($req eq "$place.1")        { $ret = $tableStart; }
    elsif   ($req eq "$place.2")        { $ret = "$place.2.1"; }
    elsif   ($req eq "$place.3")        { $ret = "$place.3.1"; }
    elsif   ($req eq "$place.1.1")      { $ret = "$place.1.2"; }
    elsif   ($req eq "$place.1.2")      { $ret = "$place.1.3"; }
    elsif   ($req eq "$place.1.3")      { $ret = "$place.2.1"; }
    elsif   ($req eq "$place.2.1")      { $ret = "$place.2.2"; }
    elsif   ($req eq "$place.2.2")      { $ret = "$place.2.3"; }
    elsif   ($req eq "$place.2.3")      { $ret = "$place.3.1"; }
    elsif   ($req eq "$place.3.1")      { $ret = "$place.3.2"; }
    elsif   ($req eq "$place.3.2")      { $ret = "$place.3.3"; }
    elsif   ($req eq "$place.3.3")      { exit 0; }
    else                                { exit 0; }
}
else 
{
#  GET requests - check for valid instance
  if ( index($req, "$place.1.") >= 0 ||
       index($req, "$place.2.") >= 0 ||
       index($req, "$place.3.") >= 0)
  { 
    $ret = $req;
  }
  else 
    { exit 0;}
}

my $readingTemp     = getValue('/tmp/es_temperature.txt');
my $readingHumidity = getValue('/tmp/es_humidity.txt');
my $readingLight    = getValue('/tmp/es_light.txt');

#  "Process" GET* requests - return hard-coded value
#
print "$ret\n";
   if ($ret eq "$place.1.1")     { print "integer\n1\n"; exit 0;}
elsif ($ret eq "$place.1.2")     { print "integer\n2\n"; exit 0;}
elsif ($ret eq "$place.1.3")     { print "integer\n3\n"; exit 0;}
elsif ($ret eq "$place.2.1")     { print "string\nTemperature\n";   exit 0;}
elsif ($ret eq "$place.2.2")     { print "string\nHumidity\n";      exit 0;}
elsif ($ret eq "$place.2.3")     { print "string\nLight\n";         exit 0;}
elsif ($ret eq "$place.3.1")     { print "integer\n$readingTemp\n";     exit 0;}
elsif ($ret eq "$place.3.2")     { print "integer\n$readingHumidity\n"; exit 0;}
elsif ($ret eq "$place.3.3")     { print "integer\n$readingLight\n";    exit 0;}
else                             { print "string\nack... $ret $req\n";  exit 0;}  # Should not happen
