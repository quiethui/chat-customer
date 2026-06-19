export interface LoginDTO {
  username: string;
  password: string;
  code?: string;
  confirmPassword?: string;
}

export interface LoginVO {
  access_token?: string;
  token?: string;
  userInfo?: LoginUser;
}

export interface LoginUser {
  avatar?: string;
  browser?: string;
  deptId?: number;
  deptName?: string;
  expireTime?: number;
  ipaddr?: string;
  loginId?: string;
  loginLocation?: string;
  loginTime?: number;
  menuPermission?: string[];
  nickName?: string;
  os?: string;
  roleId?: number;
  rolePermission?: string[];
  roles?: RoleDTO[];
  tenantId?: string;
  token?: string;
  userId?: number;
  username?: string;
  userType?: string;
}

export interface RoleDTO {
  dataScope?: string;
  roleId?: number;
  roleKey?: string;
  roleName?: string;
}

export interface EmailCodeDTO {
  username?: string;
}

export interface RegisterDTO {
  username: string;
  password: string;
  code?: string;
  confirmPassword?: string;
}
